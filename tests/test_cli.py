"""Tests for CLI user-facing behavior."""

import subprocess
import sys


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "awescholar.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_help_does_not_load_litellm():
    result = _run_cli("--help")

    combined = result.stdout + result.stderr
    assert result.returncode == 0
    assert "LiteLLM" not in combined
    assert "usage: awescholar" in combined


def test_version_uses_package_version_without_litellm_warning():
    result = _run_cli("-v")

    combined = result.stdout + result.stderr
    assert result.returncode == 0
    assert combined.strip() == "awescholar 0.1.3"
    assert "LiteLLM" not in combined
