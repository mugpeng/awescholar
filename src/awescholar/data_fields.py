"""Project data field normalization."""

PROJECT_PAPER_FIELDS = (
    "year",
    "title",
    "team",
    "team website",
    "affiliation",
    "domain",
    "venue",
    "paperUrl",
    "codeUrl",
    "githubStars",
    "doi",
)

FIELD_ALIASES = {
    "year": ("year", "publication_date", "publicationDate"),
    "title": ("title",),
    "team": ("team",),
    "team website": ("team website", "team_website", "teamWebsite"),
    "affiliation": ("affiliation",),
    "domain": ("domain",),
    "venue": ("venue", "journal"),
    "paperUrl": ("paperUrl", "paper_url", "url"),
    "codeUrl": ("codeUrl", "code_url", "codeURL"),
    "githubStars": ("githubStars", "github_stars", "githubStarsUrl"),
    "doi": ("doi", "DOI"),
}


def first_present(data: dict, *keys: str, default: str = ""):
    """Return the first non-empty value for any key."""
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def normalize_project_paper_fields(paper: dict) -> dict:
    """Project data fields only — drops everything else."""
    entry = {}
    for field in PROJECT_PAPER_FIELDS:
        entry[field] = first_present(paper, *FIELD_ALIASES[field])

    year = entry.get("year")
    if isinstance(year, str) and len(year) >= 7:
        entry["year"] = year[:7]

    return entry


def merge_preserving_nonempty(existing: dict, incoming: dict) -> dict:
    """Merge incoming fields without clearing existing non-empty values."""
    merged = {**existing}
    for key, value in incoming.items():
        if value in (None, "") and existing.get(key) not in (None, ""):
            continue
        merged[key] = value
    return merged
