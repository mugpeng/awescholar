"""Utilities: JSON merge, README generation, RSS feed."""

import json
import os
import shutil
import html
from datetime import datetime

from .categories import canonicalize_category, find_matching_category

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

        existing_dois = {p["doi"] for p in archive[target_category]}
        for paper in papers:
            entry = {**paper}
            if "category" in entry:
                entry["category"] = target_category
            if entry["doi"] not in existing_dois:
                archive[target_category].append(entry)
                existing_dois.add(entry["doi"])
            else:
                # Update existing entry
                for i, existing in enumerate(archive[target_category]):
                    if existing["doi"] == entry["doi"]:
                        archive[target_category][i] = {**existing, **entry}
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

        existing_dois = {p["doi"] for p in new_data[target_category]}
        for paper in archive_papers:
            if paper["doi"] not in existing_dois:
                entry = {**paper}
                if "category" in entry:
                    entry["category"] = target_category
                new_data[target_category].append(entry)
                existing_dois.add(entry["doi"])

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
            entry = {**paper}
            if "category" in entry:
                entry["category"] = target_category
            sections[target_category].append(entry)
    return sections


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

    Reads the archive, generates markdown tables for each category,
    and writes/updates the README preserving any manual header content.
    """
    with open(archive_path, "r", encoding="utf-8") as f:
        archive = json.load(f)

    archive = _canonical_archive_sections(archive)
    toc_lines = []
    table_sections = []

    for category, papers in archive.items():
        if not papers:
            continue

        toc_lines.append(f"- [{category}](#{_format_anchor(category)})")

        # Sort by year descending
        sorted_papers = sorted(papers, key=lambda p: p.get("year") or 0, reverse=True)

        lines = [f"## {category}"]
        lines.append("")
        lines.append("| Year | Title | Team | Team Website | Affiliation | Domain | Venue | Paper/ Source | Code/Product |")
        lines.append("| -----| ------| -----| -------------| ------------| -------| ------| --------------| -------------|")

        for p in sorted_papers:
            year = p.get("year") or p.get("publication_date", "")
            if isinstance(year, str) and len(year) >= 7:
                year = year[:7]  # YYYY-MM

            title = _escape_md(p.get("title", ""))
            team = _escape_md(p.get("team", ""))
            team_website = p.get("team_website", "")
            affiliation = _escape_md(p.get("affiliation", ""))
            domain = _escape_md(p.get("domain", ""))
            venue = _escape_md(p.get("venue", ""))

            doi = p.get("doi", "")
            paper_url = p.get("url", "")
            if not paper_url and doi:
                paper_url = f"https://doi.org/{doi}"
            paper_link = f"[Link]({paper_url})" if paper_url else ""

            code_url = p.get("code_url", "")
            code_link = f"[Link]({code_url})" if code_url else ""

            lines.append(
                f"| {year} | **{title}** | {team} | {team_website} | {affiliation} | {domain} | {venue} | {paper_link} | {code_link} |"
            )

        table_sections.append("\n".join(lines))

    generated_parts = ["## Table of Contents", *toc_lines, "", *table_sections]
    generated_content = "\n\n".join(generated_parts).strip() + "\n"

    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
        if README_START_MARKER not in existing_content or README_END_MARKER not in existing_content:
            raise RuntimeError(
                f"README update requires {README_START_MARKER} and {README_END_MARKER} markers."
            )
        before, rest = existing_content.split(README_START_MARKER, 1)
        _, after = rest.split(README_END_MARKER, 1)
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


def generate_rss(
    archive_path: str,
    output_path: str,
    title: str = "Awesome Scholar Updates",
    link: str = "",
    description: str = "Latest papers from curated collection",
):
    """Generate RSS feed from archive JSON."""
    with open(archive_path, "r", encoding="utf-8") as f:
        archive = json.load(f)

    items = []
    for category, papers in archive.items():
        for p in papers:
            pub_date = p.get("publication_date", "")
            title_text = html.escape(p.get("title", "Untitled"))
            desc = html.escape(p.get("abstract", "")[:500])
            doi = p.get("doi", "")
            url = p.get("url", "") or (f"https://doi.org/{doi}" if doi else "")

            items.append(f"""<item>
  <title>{title_text}</title>
  <link>{html.escape(url)}</link>
  <description>{desc}</description>
  <category>{html.escape(category)}</category>
  <pubDate>{pub_date}</pubDate>
  <guid>{html.escape(url)}</guid>
</item>""")

    now = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{html.escape(title)}</title>
  <link>{html.escape(link)}</link>
  <description>{html.escape(description)}</description>
  <lastBuildDate>{now}</lastBuildDate>
  {"".join(items)}
</channel>
</rss>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rss)

    return output_path
