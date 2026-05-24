"""Utilities: JSON merge, README generation, RSS feed."""

import json
import os
import re
import shutil
import html
from datetime import datetime

from .categories import canonicalize_category, find_matching_category, normalize_category_name
from .data_fields import first_present, merge_preserving_nonempty, normalize_project_paper_fields

README_START_MARKER = "<!-- AWESCHOLAR:START -->"
README_END_MARKER = "<!-- AWESCHOLAR:END -->"


def merge_new_to_archive(new_path: str, archive_path: str) -> dict:
    """Merge new filtered data into cumulative archive JSON.

    Deduplicates by DOI. New papers are added; existing papers are updated.
    Returns the merged archive.
    """
    with open(new_path, "r", encoding="utf-8") as f:
        new_data = json.load(f)

    if os.path.exists(archive_path):
        with open(archive_path, "r", encoding="utf-8") as f:
            archive = json.load(f)
    else:
        archive = {}

    for category, papers in new_data.items():
        target_category = canonicalize_category(category, archive.keys())
        if target_category not in archive:
            archive[target_category] = []

        existing_dois = {p.get("doi") for p in archive[target_category] if p.get("doi")}
        for paper in papers:
            entry = normalize_project_paper_fields(paper)
            if "category" in entry:
                entry["category"] = target_category
            doi = entry.get("doi")
            if not doi:
                archive[target_category].append(entry)
            elif doi not in existing_dois:
                archive[target_category].append(entry)
                existing_dois.add(doi)
            else:
                # Update existing entry
                for i, existing in enumerate(archive[target_category]):
                    if existing.get("doi") == doi:
                        archive[target_category][i] = merge_preserving_nonempty(existing, entry)
                        break

    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(archive, f, indent=2, ensure_ascii=False)

    return archive


def merge_archive_to_new(new_path: str, archive_path: str) -> dict:
    """Enrich new data with relevant papers from the archive.

    For each category in new_data, also include papers from the archive
    that belong to the same category. Returns the enriched new data.
    """
    if not os.path.exists(archive_path):
        with open(new_path, "r", encoding="utf-8") as f:
            return json.load(f)

    with open(new_path, "r", encoding="utf-8") as f:
        new_data = json.load(f)
    with open(archive_path, "r", encoding="utf-8") as f:
        archive = json.load(f)

    for category, archive_papers in archive.items():
        target_category = canonicalize_category(category, new_data.keys())
        if target_category not in new_data:
            new_data[target_category] = []

        existing_dois = {p.get("doi") for p in new_data[target_category] if p.get("doi")}
        for paper in archive_papers:
            doi = paper.get("doi")
            if not doi or doi not in existing_dois:
                entry = normalize_project_paper_fields(paper)
                if "category" in entry:
                    entry["category"] = target_category
                new_data[target_category].append(entry)
                if doi:
                    existing_dois.add(doi)

    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)

    return new_data


def _escape_md(text: str) -> str:
    """Escape pipe characters for markdown tables."""
    if not text:
        return ""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _format_anchor(category: str) -> str:
    return (
        str(category)
        .strip()
        .lower()
        .replace("&", "")
        .replace("/", "")
        .replace(" ", "-")
    )


def _canonical_archive_sections(archive: dict) -> dict:
    sections = {}
    for category, papers in archive.items():
        if not papers:
            continue
        target_category = find_matching_category(category, sections.keys()) or category
        sections.setdefault(target_category, [])
        for paper in papers:
            entry = normalize_project_paper_fields(paper)
            if "category" in entry:
                entry["category"] = target_category
            sections[target_category].append(entry)
    return sections


def _format_link(url: str) -> str:
    if not url:
        return ""
    if str(url).startswith("["):
        return str(url)
    return f"[Link]({url})"


def _format_code_product(code_url: str, github_stars: str) -> str:
    parts = []
    if code_url:
        parts.append(_format_link(code_url))
    if github_stars:
        parts.append(f"![GitHub Stars]({github_stars})")
    return " ".join(parts)


def _parse_existing_sections(content: str) -> dict:
    """Parse existing section headers and their boundaries from content.

    Returns {normalized_name: original_header_line} for each ## section.
    """
    sections = {}
    for line in content.splitlines():
        if line.startswith("## "):
            key = normalize_category_name(line[3:].strip())
            if key:
                sections[key] = line
    return sections


def _parse_existing_toc(content: str) -> list:
    """Extract existing TOC lines from content (lines starting with '- [')."""
    toc = []
    in_toc = False
    for line in content.splitlines():
        if line.startswith("## "):
            if in_toc:
                break
            if "table of contents" in line.lower():
                in_toc = True
                continue
        elif in_toc and line.startswith("- ["):
            toc.append(line)
    return toc


def _split_sections(content: str) -> tuple:
    """Split content into (toc_block, section_blocks, trailing).

    Returns (toc_text, {normalized_name: section_text}, trailing_text_after_last_section).
    """
    lines = content.splitlines(keepends=True)
    toc_block = ""
    sections = {}
    current_key = None
    current_lines = []
    trailing_lines = []
    in_toc = False
    toc_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            header_text = stripped[3:].strip()
            if "table of contents" in header_text.lower():
                in_toc = True
                continue
            # Save previous section
            if current_key is not None:
                sections[current_key] = "".join(current_lines)
            elif in_toc:
                toc_block = "".join(toc_lines)
                in_toc = False
            current_key = normalize_category_name(header_text)
            current_lines = [line]
        elif in_toc:
            toc_lines.append(line)
        elif current_key is not None:
            current_lines.append(line)
        # Lines before TOC or between TOC and first section are ignored
        # (they're in the before/after parts of the marker split)

    if current_key is not None:
        sections[current_key] = "".join(current_lines)
    if in_toc:
        toc_block = "".join(toc_lines)

    return toc_block, sections


def update_readme(
    archive_path: str,
    readme_path: str,
    project_title: str = "Awesome Scholar",
    project_description: str = "",
    website_url: str = "",
    github_repo: str = "",
    no_backup: bool = False,
):
    """Generate/update README.md tables from archive JSON.

    Preserves existing TOC entries and section headers (including emojis,
    custom names, custom anchors). Only updates table rows for existing
    categories and appends new categories at the end.
    """
    with open(archive_path, "r", encoding="utf-8") as f:
        archive = json.load(f)

    archive = _canonical_archive_sections(archive)

    def _sort_year(p):
        y = p.get("year") or ""
        if isinstance(y, str):
            return y
        return str(y)

    def _make_table_rows(papers):
        """Generate only the table header + rows (no ## heading)."""
        sorted_papers = sorted(papers, key=_sort_year, reverse=True)
        lines = [
            "| Year | Title | Team | Team Website | Affiliation | Domain | Venue | Paper/ Source | Code/Product |",
            "| -----| ------| -----| -------------| ------------| -------| ------| --------------| -------------|",
        ]
        for p in sorted_papers:
            year = p.get("year") or p.get("publication_date", "")
            if isinstance(year, str) and len(year) >= 7:
                year = year[:7]
            title = _escape_md(p.get("title", ""))
            team = _escape_md(p.get("team", ""))
            team_website = _format_link(first_present(p, "team website", "team_website"))
            affiliation = _escape_md(p.get("affiliation", ""))
            domain = _escape_md(p.get("domain", ""))
            venue = _escape_md(p.get("venue", ""))
            doi = p.get("doi", "")
            paper_url = first_present(p, "paperUrl", "paper_url", "url")
            if not paper_url and doi:
                paper_url = f"https://doi.org/{doi}"
            paper_link = _format_link(paper_url)
            code_url = first_present(p, "codeUrl", "code_url")
            github_stars = first_present(p, "githubStars", "github_stars")
            code_link = _format_code_product(code_url, github_stars)
            lines.append(
                f"| {year} | **{title}** | {team} | {team_website} | {affiliation} | {domain} | {venue} | {paper_link} | {code_link} |"
            )
        return "\n".join(lines)

    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
        if README_START_MARKER not in existing_content or README_END_MARKER not in existing_content:
            raise RuntimeError(
                f"README update requires {README_START_MARKER} and {README_END_MARKER} markers."
            )
        before, rest = existing_content.split(README_START_MARKER, 1)
        inner, after = rest.split(README_END_MARKER, 1)

        # Parse existing sections from the inner content (between markers)
        _, existing_sections = _split_sections(inner)

        # Build new content: preserve existing sections, update tables
        section_parts = []
        new_toc_entries = []

        for category, papers in archive.items():
            if not papers:
                continue
            norm = normalize_category_name(category)
            if norm in existing_sections:
                # Preserve existing section header, update table rows
                existing_block = existing_sections[norm]
                header_line = existing_block.splitlines()[0] if existing_block.splitlines() else f"## {category}"
                table_rows = _make_table_rows(papers)
                section_parts.append(f"{header_line}\n\n{table_rows}")
            else:
                # New category — generate section and TOC entry
                table_rows = _make_table_rows(papers)
                section_parts.append(f"## {category}\n\n{table_rows}")
                anchor = _format_anchor(category)
                new_toc_entries.append(f"- [{category}](#{anchor})")

        generated_content = "\n\n".join(section_parts) + "\n"

        # Append new TOC entries to the TOC in the 'before' part
        if new_toc_entries:
            before_lines = before.rstrip("\n").split("\n")
            # Find last TOC line (starts with '- [') and insert after it
            last_toc_idx = -1
            for i, line in enumerate(before_lines):
                if line.strip().startswith("- ["):
                    last_toc_idx = i
            if last_toc_idx >= 0:
                for entry in reversed(new_toc_entries):
                    before_lines.insert(last_toc_idx + 1, entry)
                before = "\n".join(before_lines) + "\n"

        content = (
            f"{before}{README_START_MARKER}\n"
            f"{generated_content}"
            f"{README_END_MARKER}{after}"
        )
    else:
        parts = [f"# {project_title}"]
        if project_description:
            parts.append(f"\n{project_description}")
        parts.append("")
        parts.append(README_START_MARKER)
        parts.append(generated_content.rstrip())
        parts.append(README_END_MARKER)
        parts.append("")
        content = "\n".join(parts)

    if not no_backup and os.path.exists(readme_path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{readme_path}.{ts}.bak"
        try:
            shutil.copy2(readme_path, backup_path)
            print(f"Created backup: {backup_path}")
        except Exception as e:
            print(f"Warning: Could not create backup of {readme_path}: {e}")

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)

    return readme_path


def _year_to_rfc822(year_str: str) -> str:
    """Convert '2025.12' or '2025-12' to RFC 822 date like 'Mon, 01 Dec 2025 00:00:00 GMT'."""
    if not year_str:
        return ""
    normalized = year_str.replace(".", "-")
    try:
        dt = datetime.strptime(normalized[:7], "%Y-%m")
        return dt.strftime("%a, %d %b %Y 00:00:00 GMT")
    except (ValueError, IndexError):
        return year_str


def _guid_from_paper(title: str, year: str) -> str:
    """Generate a stable guid: strip non-alpha, concat title+year."""
    clean = re.sub(r"[^a-zA-Z]", "", title)
    y = (year or "").replace(".", "")
    return f"{clean}{y}"


def generate_rss(
    archive_path: str,
    output_path: str,
    title: str = "Awesome Scholar Updates",
    link: str = "",
    description: str = "Latest papers from curated collection",
    rss_url: str = "",
):
    """Generate RSS feed from archive JSON.

    If the output file already exists, preserves its channel metadata
    (title, link, description, atom:link) unless explicitly overridden.
    """
    # Preserve existing metadata when regenerating
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = f.read()
        if title == "Awesome Scholar Updates":
            m = re.search(r"<title>(.*?)</title>", existing)
            if m:
                title = m.group(1)
        if not link:
            m = re.search(r"<link>(.*?)</link>", existing)
            if m:
                link = m.group(1)
        if description == "Latest papers from curated collection":
            m = re.search(r"<description>(.*?)</description>", existing, re.DOTALL)
            if m:
                description = m.group(1).strip()
        if not rss_url:
            m = re.search(r'<atom:link href="(.*?)"', existing)
            if m:
                rss_url = m.group(1)

    with open(archive_path, "r", encoding="utf-8") as f:
        archive = json.load(f)

    items = []
    for category, papers in archive.items():
        for p in papers:
            ptitle = p.get("title", "Untitled")
            team = p.get("team", "")
            domain = p.get("domain", "")
            venue = p.get("venue", "")
            doi = p.get("doi", "")
            year = p.get("year", "")
            paper_url = p.get("paperUrl", "") or (f"https://doi.org/{doi}" if doi else "")
            code_url = p.get("codeUrl", "")

            # Prefer DOI link for the item link
            item_link = f"https://doi.org/{doi}" if doi else paper_url

            desc_parts = [f"<p><b>Team:</b> {html.escape(team)}</p>"]
            if domain:
                desc_parts.append(f"<p><b>Domain:</b> {html.escape(domain)}</p>")
            if venue:
                desc_parts.append(f"<p><b>Venue:</b> {html.escape(venue)}</p>")
            if paper_url:
                desc_parts.append(f'<p><a href="{html.escape(paper_url)}">Read the Paper</a></p>')
            if code_url:
                desc_parts.append(f'<p><a href="{html.escape(code_url)}">Code</a></p>')
            cdata = "\n        ".join(desc_parts)

            pub_date = _year_to_rfc822(year)
            guid = _guid_from_paper(ptitle, year)

            items.append(f"""  <item>
    <title>{html.escape(ptitle)}</title>
    <link>{html.escape(item_link)}</link>
    <description>
      <![CDATA[
        {cdata}
      ]]>
    </description>
    <pubDate>{pub_date}</pubDate>
    <guid isPermaLink="false">{guid}</guid>
  </item>""")

    now = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
    atom_link = f'\n  <atom:link href="{html.escape(rss_url)}" rel="self" type="application/rss+xml" />' if rss_url else ""

    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{html.escape(title)}</title>
  <link>{html.escape(link)}</link>
  <description>{html.escape(description)}</description>
  <language>en-us</language>
  <lastBuildDate>{now}</lastBuildDate>{atom_link}
{chr(10).join(items)}
</channel>
</rss>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rss)

    return output_path
