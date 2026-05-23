"""Category name normalization and matching."""

import re


def normalize_category_name(name: str) -> str:
    """Normalize category names for case/separator-insensitive matching."""
    words = re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()
    return re.sub(r"\s+", " ", words)


def find_matching_category(category: str, candidates) -> str | None:
    """Return the existing candidate matching category, ignoring case and separators."""
    normalized = normalize_category_name(category)
    for candidate in candidates:
        if normalize_category_name(candidate) == normalized:
            return candidate
    return None


def canonicalize_category(category: str, candidates) -> str:
    """Map category to an existing candidate spelling when possible."""
    return find_matching_category(category, candidates) or category
