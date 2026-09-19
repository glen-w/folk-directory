"""Contracts for relaunch plan surfaces: status filter, schema, submit, titles."""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "ingest"))
PUBLIC = ROOT / "public"
INDEX = PUBLIC / "listings" / "index.json"
HOME = PUBLIC / "index.html"
SUBMIT = PUBLIC / "submit" / "index.html"
CLAIM = PUBLIC / "claim" / "index.html"
BROWSE_JS = ROOT / "static" / "js" / "listings-browse.js"
FASTSEARCH = ROOT / "assets" / "js" / "fastsearch.js"
SCHEMA = ROOT / "layouts" / "_partials" / "templates" / "schema_json.html"
DUP_TITLES = ROOT / "data" / "dup-titles.json"
LISTINGS = ROOT / "content" / "listings"


def _ensure_build() -> None:
    if INDEX.exists() and HOME.exists() and SUBMIT.exists() and CLAIM.exists():
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


def test_no_placeholder_listing_titles():
    from listing_fields import is_placeholder_name  # noqa: E402

    offenders = []
    for path in LISTINGS.glob("*.md"):
        if path.name == "_index.md":
            continue
        text = path.read_text(encoding="utf-8")
        title_m = re.search(r"^title:\s*(.+)$", text, re.M)
        name_m = re.search(r"^name:\s*(.+)$", text, re.M)
        title = (title_m.group(1).strip().strip("\"'") if title_m else "")
        name = (name_m.group(1).strip().strip("\"'") if name_m else "")
        if is_placeholder_name(title) or is_placeholder_name(name) or re.fullmatch(
            r"listing-\d+", path.stem
        ):
            offenders.append(path.name)
    assert not offenders, f"placeholder listing names remain: {offenders[:20]}"


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


def test_address_does_not_repeat_place():
    """`place` is shown on its own line, so it must not also be an address segment."""

    street_re = re.compile(
        r"(?i)\b(road|street|lane|avenue|close|drive|way|terrace|crescent|"
        r"square|row|quay|court|hill|gardens?|parade|grove|walk|mews|gate|"
        r"circus|rd|st|ln|ave)\b"
    )
    saint_town_re = re.compile(
        r"(?i)(^st\.?\s+|\bst\.?\s+(neots|albans|ives|edmunds|andrew|leonards)\b)"
    )
    house_re = re.compile(r"^\d+[a-z]?(?:\s*[-/]\s*\d+[a-z]?)?\s+", re.I)

    def norm(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip(" .,").lower()

    def fold_street(value: str) -> str:
        value = house_re.sub("", norm(value).replace(".", ""))
        value = re.sub(r"\bstreet\b", "st", value)
        value = re.sub(r"\broad\b", "rd", value)
        value = re.sub(r"\blane\b", "ln", value)
        value = re.sub(r"\bavenue\b", "ave", value)
        return re.sub(r"\s+", " ", value).strip()

    def looks_like_street(value: str) -> bool:
        if saint_town_re.search(value):
            return False
        return bool(street_re.search(value))

    offenders = []
    for path in LISTINGS.glob("*.md"):
        if path.name == "_index.md":
            continue
        text = path.read_text(encoding="utf-8")
        fm = re.match(r"^---\n(.*?)\n---", text, re.S)
        if not fm:
            continue
        block = fm.group(1)
        addr_m = re.search(r"^address:\s*(.*)$", block, re.M)
        place_m = re.search(r"^place:\s*(.*)$", block, re.M)
        if not addr_m or not place_m:
            continue
        address = addr_m.group(1).strip().strip("\"'")
        place = place_m.group(1).strip().strip("\"'")
        if not address or not place:
            continue
        if any(norm(part) == norm(place) for part in address.split(",") if part.strip()):
            offenders.append(path.name)
            continue
        place_head = place.split(",")[0].strip()
        folded_place = fold_street(place_head)
        folded_addr = fold_street(address)
        if (
            looks_like_street(place_head)
            and folded_place
            and (folded_addr == folded_place or folded_addr.endswith(" " + folded_place))
        ):
            offenders.append(path.name)
    assert not offenders, f"address repeats place: {offenders[:20]}"


def test_address_does_not_include_country():
    """Country is schema addressCountry / a geocode hint, not a street segment."""
    country_re = re.compile(
        r"(?i)(?:^|,\s*)(?:united\s+kingdom|great\s+britain|u\.k\.|uk)\s*[.]?\s*$"
    )
    offenders = []
    for path in LISTINGS.glob("*.md"):
        if path.name == "_index.md":
            continue
        text = path.read_text(encoding="utf-8")
        fm = re.match(r"^---\n(.*?)\n---", text, re.S)
        if not fm:
            continue
        addr_m = re.search(r"^address:\s*(.*)$", fm.group(1), re.M)
        if not addr_m:
            continue
        address = addr_m.group(1).strip().strip("\"'")
        if address and country_re.search(address):
            offenders.append(path.name)
    assert not offenders, f"country still in address: {offenders[:20]}"


def test_address_is_never_a_coord_pin():
    """Street `address` must be human-readable; pins live in lat/lng."""
    pin_re = re.compile(
        r"^address:\s*['\"]?@\s*[+-]?\d{1,2}\.\d{3,}\s*,\s*[+-]?\d{1,3}\.\d{3,}",
        re.M,
    )
    offenders = []
    for path in LISTINGS.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if pin_re.search(text):
            offenders.append(path.name)
    assert not offenders, f"coord pins still in address: {offenders[:20]}"


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


def test_claim_page_email_only(built):
    assert CLAIM.is_file()
    html = CLAIM.read_text(encoding="utf-8")
    assert "listing-claim-form" in html
    assert "Send claim by email" in html
    assert "Open GitHub issue" not in html
    assert (ROOT / "static" / "js" / "listing-claim.js").is_file()
    for field in ("listing_id", "claimant_email", "connection", "verification"):
        assert f"name={field}" in html or f'name="{field}"' in html


def test_listing_footer_has_claim_and_update(built):
    fixture = PUBLIC / "listings" / "above-the-parapet" / "index.html"
    html_path = fixture if fixture.is_file() else next((PUBLIC / "listings").glob("*/index.html"), None)
    assert html_path and html_path.is_file(), "expected built listing pages"
    html = html_path.read_text(encoding="utf-8")
    assert "/claim/?" in html
    assert "Claim this listing" in html
    assert "Suggest an update" in html
    assert "Is this your event?" in html


def test_search_empty_state_mentions_submit():
    text = FASTSEARCH.read_text(encoding="utf-8")
    assert "No matches" in text
    assert "/submit/" in text

def test_schema_partial_uses_dict_jsonify():
    text = SCHEMA.read_text(encoding="utf-8")
    assert "jsonify | safeJS" in text
    assert "LocalBusiness" in text
