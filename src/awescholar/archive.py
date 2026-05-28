"""Archive merge operations for project data JSON."""

import json
import os
from datetime import date, datetime

from .categories import canonicalize_category
from .data_fields import merge_preserving_nonempty, normalize_project_paper_fields


class DateEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        return super().default(o)


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
