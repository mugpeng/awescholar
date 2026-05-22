"""Tests for utils.py — merge, readme, rss."""

import json
import os
import tempfile

from awescholar.utils import merge_new_to_archive, merge_archive_to_new, update_readme, generate_rss


def _write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── merge_new_to_archive ─────────────────────────────────────

def test_merge_new_creates_archive():
    with tempfile.TemporaryDirectory() as tmp:
        new = os.path.join(tmp, "new.json")
        archive = os.path.join(tmp, "archive.json")
        _write_json(new, {"Cat A": [{"doi": "10.1/a", "title": "Paper A"}]})

        result = merge_new_to_archive(new, archive)

        assert "Cat A" in result
        assert len(result["Cat A"]) == 1
        assert result["Cat A"][0]["doi"] == "10.1/a"
        assert os.path.exists(archive)


def test_merge_new_deduplicates_by_doi():
    with tempfile.TemporaryDirectory() as tmp:
        new = os.path.join(tmp, "new.json")
        archive = os.path.join(tmp, "archive.json")
        _write_json(new, {"Cat A": [{"doi": "10.1/a", "title": "Updated Title"}]})
        _write_json(archive, {"Cat A": [{"doi": "10.1/a", "title": "Old Title"}]})

        result = merge_new_to_archive(new, archive)

        assert len(result["Cat A"]) == 1
        assert result["Cat A"][0]["title"] == "Updated Title"


def test_merge_new_adds_to_existing_category():
    with tempfile.TemporaryDirectory() as tmp:
        new = os.path.join(tmp, "new.json")
        archive = os.path.join(tmp, "archive.json")
        _write_json(new, {"Cat A": [{"doi": "10.1/b", "title": "Paper B"}]})
        _write_json(archive, {"Cat A": [{"doi": "10.1/a", "title": "Paper A"}]})

        result = merge_new_to_archive(new, archive)

        assert len(result["Cat A"]) == 2


def test_merge_new_creates_new_category():
    with tempfile.TemporaryDirectory() as tmp:
        new = os.path.join(tmp, "new.json")
        archive = os.path.join(tmp, "archive.json")
        _write_json(new, {"Cat B": [{"doi": "10.1/b", "title": "Paper B"}]})
        _write_json(archive, {"Cat A": [{"doi": "10.1/a", "title": "Paper A"}]})

        result = merge_new_to_archive(new, archive)

        assert "Cat A" in result
        assert "Cat B" in result


# ── merge_archive_to_new ─────────────────────────────────────

def test_merge_archive_enriches_new():
    with tempfile.TemporaryDirectory() as tmp:
        new = os.path.join(tmp, "new.json")
        archive = os.path.join(tmp, "archive.json")
        _write_json(new, {"Cat A": [{"doi": "10.1/b", "title": "New Paper"}]})
        _write_json(archive, {"Cat A": [{"doi": "10.1/a", "title": "Archive Paper"}]})

        result = merge_archive_to_new(new, archive)

        assert len(result["Cat A"]) == 2
        dois = {p["doi"] for p in result["Cat A"]}
        assert "10.1/a" in dois
        assert "10.1/b" in dois


def test_merge_archive_no_archive():
    with tempfile.TemporaryDirectory() as tmp:
        new = os.path.join(tmp, "new.json")
        archive = os.path.join(tmp, "nonexistent.json")
        _write_json(new, {"Cat A": [{"doi": "10.1/a", "title": "Paper"}]})

        result = merge_archive_to_new(new, archive)

        assert len(result["Cat A"]) == 1


# ── update_readme ────────────────────────────────────────────

def test_update_readme_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        archive = os.path.join(tmp, "archive.json")
        readme = os.path.join(tmp, "readme.md")
        _write_json(archive, {
            "Models": [{"doi": "10.1/a", "title": "Test Paper", "year": 2025, "domain": "AI"}]
        })

        update_readme(archive, readme, project_title="Test Awesome")

        assert os.path.exists(readme)
        content = open(readme).read()
        assert "# Test Awesome" in content
        assert "Test Paper" in content
        assert "## Models" in content


def test_update_readme_creates_backup_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        archive = os.path.join(tmp, "archive.json")
        readme = os.path.join(tmp, "readme.md")
        _write_json(archive, {"Cat": [{"doi": "10.1/a", "title": "P", "year": 2025}]})
        # Create initial readme
        with open(readme, "w") as f:
            f.write("# Old Content\n")

        update_readme(archive, readme)

        # Should have exactly one .bak file
        bak_files = [f for f in os.listdir(tmp) if f.startswith("readme.md.") and f.endswith(".bak")]
        assert len(bak_files) == 1
        assert "2026" in bak_files[0] or "2025" in bak_files[0]  # has timestamp


def test_update_readme_no_backup_skips_backup():
    with tempfile.TemporaryDirectory() as tmp:
        archive = os.path.join(tmp, "archive.json")
        readme = os.path.join(tmp, "readme.md")
        _write_json(archive, {"Cat": [{"doi": "10.1/a", "title": "P", "year": 2025}]})
        with open(readme, "w") as f:
            f.write("# Old Content\n")

        update_readme(archive, readme, no_backup=True)

        bak_files = [f for f in os.listdir(tmp) if f.endswith(".bak")]
        assert bak_files == []


def test_update_readme_no_backup_no_existing_file():
    """no_backup should not error when readme doesn't exist yet."""
    with tempfile.TemporaryDirectory() as tmp:
        archive = os.path.join(tmp, "archive.json")
        readme = os.path.join(tmp, "readme.md")
        _write_json(archive, {"Cat": [{"doi": "10.1/a", "title": "P", "year": 2025}]})

        update_readme(archive, readme, no_backup=True)

        assert os.path.exists(readme)


# ── generate_rss ─────────────────────────────────────────────

def test_generate_rss_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        archive = os.path.join(tmp, "archive.json")
        rss = os.path.join(tmp, "rss.xml")
        _write_json(archive, {
            "Cat": [{"doi": "10.1/a", "title": "Paper", "abstract": "Abstract text"}]
        })

        generate_rss(archive, rss, title="Test Feed")

        assert os.path.exists(rss)
        content = open(rss).read()
        assert "<rss" in content
        assert "Paper" in content
        assert "Test Feed" in content
