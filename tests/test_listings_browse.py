"""Contracts for /listings/ browse index and filter engine semantics."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "public" / "listings" / "index.json"
LIST_HTML = ROOT / "layouts" / "listings" / "list.html"
LIST_JSON = ROOT / "layouts" / "listings" / "list.json.json"
BROWSE_JS = ROOT / "static" / "js" / "listings-browse.js"

REQUIRED_ITEM_KEYS = {
    "id",
    "title",
    "permalink",
    "summary",
    "event_types",
    "county",
    "status",
    "when",
    "venue",
    "place",
    "post_code",
    "www",
    "locations",
}


def _ensure_index() -> dict:
    if not INDEX.exists():
        subprocess.run(
            ["hugo", "--minify"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    assert data.get("version") == 1
    assert isinstance(data.get("items"), list)
    assert data["items"], "listings index should not be empty"
    return data


def match_item(item: dict, field: str, mode: str, value: str) -> bool:
    if value == "" or value is None:
        return True
    field_value = item.get(field)
    if mode == "includes":
        values = field_value if isinstance(field_value, list) else ([field_value] if field_value else [])
        return str(value) in [str(v) for v in values]
    if mode == "eq":
        return str(field_value or "") == str(value)
    if mode == "contains":
        hay = str(field_value or "").lower()
        return str(value).lower() in hay
    raise AssertionError(f"unknown match mode {mode}")


def apply_filters(items: list[dict], *, type_: str = "", county: str = "") -> list[dict]:
    out = []
    for item in items:
        if not match_item(item, "event_types", "includes", type_):
            continue
        if not match_item(item, "county", "eq", county):
            continue
        out.append(item)
    return out


def paginate(items: list[dict], page: int, page_size: int) -> dict:
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size) if page_size else 1
    safe_page = min(max(1, page), total_pages)
    start = (safe_page - 1) * page_size
    return {
        "page": safe_page,
        "total_pages": total_pages,
        "total": total,
        "items": items[start : start + page_size],
    }


def resolve_page_size(show, filtered_count: int) -> int:
    if str(show).lower() == "all":
        return max(filtered_count, 1)
    num = int(show)
    assert num > 0
    return num


@pytest.fixture(scope="module")
def index_data() -> dict:
    return _ensure_index()


def test_source_templates_exist():
    assert LIST_HTML.is_file()
    assert LIST_JSON.is_file()
    assert BROWSE_JS.is_file()


def test_list_template_has_mounts_and_no_paginate():
    text = LIST_HTML.read_text(encoding="utf-8")
    assert ".Paginate" not in text
    for needle in (
        'id="listings-filters"',
        'id="listings-results"',
        'id="listings-pagination"',
        'id="listings-status"',
        "listings-browse.js",
        "data-enabled-filters",
        "showOptions",
        "<noscript>",
    ):
        assert needle in text


def test_browse_js_registry_and_show_options():
    text = BROWSE_JS.read_text(encoding="utf-8")
    assert "const FILTERS" in text
    assert 'param: "type"' in text
    assert 'param: "county"' in text
    assert 'match: "includes"' in text
    assert 'match: "eq"' in text
    assert 'case "contains"' in text
    assert 'case "anyOf"' in text
    assert "showOptions: [10, 25, 50, 100, \"all\"]" in text
    assert "defaultShow: 25" in text
    assert "history.replaceState" in text


def test_index_schema(index_data):
    item = index_data["items"][0]
    assert REQUIRED_ITEM_KEYS <= set(item.keys())
    assert isinstance(item["event_types"], list)
    assert isinstance(item["locations"], list)
    assert isinstance(item["county"], str)
    assert isinstance(item["www"], str)
    assert item["permalink"].startswith("/listings/")


def test_index_has_many_www_values(index_data):
    with_www = [i for i in index_data["items"] if (i.get("www") or "").strip()]
    assert len(with_www) >= 700


def test_filter_type_and_county_and(index_data):
    items = index_data["items"]
    festivals = apply_filters(items, type_="festival")
    assert festivals
    assert all("festival" in (i.get("event_types") or []) for i in festivals)

    county = next(
        (i["county"] for i in festivals if (i.get("county") or "").strip()),
        "",
    )
    assert county
    both = apply_filters(items, type_="festival", county=county)
    assert both
    assert all(
        "festival" in (i.get("event_types") or []) and i.get("county") == county
        for i in both
    )
    assert len(both) <= len(festivals)


def test_unknown_filter_value_empty(index_data):
    assert apply_filters(index_data["items"], type_="not-a-real-type") == []
    assert apply_filters(index_data["items"], county="NotARealCountyZZZ") == []


def test_show_sizes_and_all(index_data):
    items = sorted(index_data["items"], key=lambda i: i["title"].lower())
    for show in (10, 25, 50, 100):
        size = resolve_page_size(show, len(items))
        page = paginate(items, 1, size)
        assert len(page["items"]) == min(size, len(items))
        assert page["page"] == 1

    all_size = resolve_page_size("all", len(items))
    page = paginate(items, 1, all_size)
    assert len(page["items"]) == len(items)
    assert page["total_pages"] == 1


def test_page_clamp(index_data):
    items = index_data["items"][:30]
    page = paginate(items, 999, 10)
    assert page["page"] == 3
    assert len(page["items"]) == 10


def test_built_list_html_references_index():
    built = ROOT / "public" / "listings" / "index.html"
    if not built.exists():
        pytest.skip("public/listings/index.html missing; run hugo --minify")
    html = built.read_text(encoding="utf-8")
    assert "listings-browse" in html
    assert "/listings/index.json" in html or "listings/index.json" in html
    assert re.search(r"listings-browse\.js", html)
