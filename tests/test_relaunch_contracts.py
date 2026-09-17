"""Contracts for relaunch plan surfaces: status filter, schema, submit, titles."""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
INDEX = PUBLIC / "listings" / "index.json"
HOME = PUBLIC / "index.html"
SUBMIT = PUBLIC / "submit" / "index.html"
BROWSE_JS = ROOT / "static" / "js" / "listings-browse.js"
FASTSEARCH = ROOT / "assets" / "js" / "fastsearch.js"
SCHEMA = ROOT / "layouts" / "_partials" / "templates" / "schema_json.html"
DUP_TITLES = ROOT / "data" / "dup-titles.json"
LISTINGS = ROOT / "content" / "listings"


def _ensure_build() -> None:
    if INDEX.exists() and HOME.exists() and SUBMIT.exists():
        return
    subprocess.run(
        ["hugo", "--minify"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def built() -> None:
    _ensure_build()


def status_mode_match(status: str, mode: str) -> bool:
    """Mirror listings-browse.js statusMode semantics."""
    status = (status or "listed").lower()
    mode = (mode or "active").lower()
    if mode == "all":
        return True
    if mode == "defunct":
        return status == "defunct"
    return status != "defunct"


def test_status_mode_semantics():
    assert status_mode_match("listed", "active")
    assert status_mode_match("", "active")
    assert not status_mode_match("defunct", "active")
    assert status_mode_match("defunct", "defunct")
    assert not status_mode_match("listed", "defunct")
    assert status_mode_match("defunct", "all")
    assert status_mode_match("listed", "all")


def test_browse_js_has_status_default_and_q(built):
    text = BROWSE_JS.read_text(encoding="utf-8")
    assert 'defaultValue: "active"' in text
    assert 'match: "statusMode"' in text
    assert 'param: "q"' in text
    assert "listings-card-website" in text
    assert 'href="/submit/"' in text


def test_index_hides_need_for_www_field(built):
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    assert data["items"], "empty listings index"
    assert "www" in data["items"][0]
    with_www = [i for i in data["items"] if (i.get("www") or "").strip()]
    assert len(with_www) >= 700
    defunct = [i for i in data["items"] if str(i.get("status", "")).lower() == "defunct"]
    assert defunct, "expected some defunct listings in corpus"
    active = [i for i in data["items"] if status_mode_match(i.get("status", ""), "active")]
    assert len(active) == len(data["items"]) - len(defunct)


def test_no_duplicate_listing_titles():
    titles = []
    for path in LISTINGS.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        m = re.search(r"^title:\s*(.+)$", text, re.M)
        if m:
            titles.append(m.group(1).strip().strip("\"'"))
    counts = Counter(titles)
    dups = {t: n for t, n in counts.items() if n > 1}
    assert not dups, f"duplicate titles remain: {dups}"


def test_dup_titles_export_exists():
    assert DUP_TITLES.is_file()
    data = json.loads(DUP_TITLES.read_text(encoding="utf-8"))
    assert "groups_before_disambiguation" in data
    assert "renames" in data


def test_home_organization_schema_no_mailto(built):
    html = HOME.read_text(encoding="utf-8")
    blocks = re.findall(
        r'<script type=application/ld\+json>(.*?)</script>',
        html,
        flags=re.S,
    )
    if not blocks:
        blocks = re.findall(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            html,
            flags=re.S,
        )
    assert blocks, "expected JSON-LD on homepage"
    org = None
    for raw in blocks:
        data = json.loads(raw)
        if data.get("@type") == "Organization":
            org = data
            break
    assert org is not None
    same_as = org.get("sameAs") or []
    assert same_as
    assert all(isinstance(x, str) for x in same_as)
    assert all("mailto:" not in x for x in same_as)
    assert any("/contact/" in x for x in same_as)


def test_listing_page_uses_local_business(built):
    page = PUBLIC / "listings" / "aberdeen-folk-club" / "index.html"
    if not page.exists():
        pytest.skip("aberdeen-folk-club not in public build")
    html = page.read_text(encoding="utf-8")
    assert "BlogPosting" not in html
    blocks = re.findall(
        r'<script type=application/ld\+json>(.*?)</script>',
        html,
        flags=re.S,
    )
    if not blocks:
        blocks = re.findall(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            html,
            flags=re.S,
        )
    types = [json.loads(b).get("@type") for b in blocks]
    assert "LocalBusiness" in types


def test_submit_page_and_issue_template(built):
    assert SUBMIT.is_file()
    html = SUBMIT.read_text(encoding="utf-8")
    assert "listing-submit-form" in html
    assert "Send by email" in html
    assert "Open GitHub issue" in html
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "listing.yml").is_file()


def test_search_empty_state_mentions_submit():
    text = FASTSEARCH.read_text(encoding="utf-8")
    assert "No matches" in text
    assert "/submit/" in text


def test_schema_partial_uses_dict_jsonify():
    text = SCHEMA.read_text(encoding="utf-8")
    assert "jsonify | safeJS" in text
    assert "LocalBusiness" in text
