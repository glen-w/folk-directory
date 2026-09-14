"""Contracts for PaperMod client-side search (/index.json)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "public" / "index.json"
SEARCH_HTML = ROOT / "public" / "search" / "index.html"

REQUIRED_ITEM_KEYS = {
    "title",
    "permalink",
    "summary",
    "content",
    "venue",
    "place",
    "county",
    "event_types",
}


def _ensure_build() -> None:
    if INDEX.exists() and SEARCH_HTML.exists():
        return
    subprocess.run(
        ["hugo", "--minify"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_home_search_index_is_json_array():
    _ensure_build()
    assert INDEX.exists(), "public/index.json missing; home must output JSON for search"
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    assert isinstance(data, list), "search index must be a JSON array"
    assert data, "search index should not be empty"
    item = data[0]
    missing = REQUIRED_ITEM_KEYS - set(item)
    assert not missing, f"search index item missing keys: {sorted(missing)}"


def test_search_page_loads_index_and_script():
    _ensure_build()
    if not SEARCH_HTML.exists():
        pytest.skip("public/search/index.html missing; run hugo --minify")
    html = SEARCH_HTML.read_text(encoding="utf-8")
    assert "searchInput" in html
    assert "searchbox" in html
    assert "../index.json" in html
    assert "/assets/js/search." in html
