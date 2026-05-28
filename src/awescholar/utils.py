"""Utilities — re-exports from archive, readme, and rss modules.

This module exists for backwards compatibility. Import from the
sub-modules directly in new code.
"""

from .archive import DateEncoder, merge_archive_to_new, merge_new_to_archive
from .readme import (
    README_END_MARKER,
    README_START_MARKER,
    discover_readme_targets,
    update_readme,
)
from .rss import generate_rss

__all__ = [
    "DateEncoder",
    "merge_new_to_archive",
    "merge_archive_to_new",
    "discover_readme_targets",
    "update_readme",
    "generate_rss",
    "README_START_MARKER",
    "README_END_MARKER",
]
