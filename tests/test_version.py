"""Tests that packaging metadata stays consistent."""

import re
from importlib.metadata import version
from pathlib import Path

from wavhost.config import VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_version_matches_installed_package():
    assert VERSION == version("wavhost")


def test_runtime_version_matches_pyproject():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match is not None
    assert VERSION == match.group(1)
