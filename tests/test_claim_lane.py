"""Contracts for the light email-only claim-your-event lane."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CLAIM = PUBLIC / "claim" / "index.html"
CLAIM_JS = ROOT / "static" / "js" / "listing-claim.js"
CLAIM_MD = ROOT / "content" / "claim.md"
CLAIM_LAYOUT = ROOT / "layouts" / "_default" / "claim.html"
LISTING_SINGLE = ROOT / "layouts" / "listings" / "single.html"
HUGO_TOML = ROOT / "hugo.toml"
CONTACT = ROOT / "content" / "contact.md"
ABOUT = ROOT / "content" / "about.md"
FIXTURE_PUBLIC = PUBLIC / "listings" / "above-the-parapet" / "index.html"
ISSUE_TEMPLATES = ROOT / ".github" / "ISSUE_TEMPLATE"


def _claim_sources_newer_than_build() -> bool:
    if not CLAIM.exists():
        return True
    built_mtime = CLAIM.stat().st_mtime
    for path in (CLAIM_MD, CLAIM_LAYOUT, CLAIM_JS, LISTING_SINGLE, HUGO_TOML):
        if path.exists() and path.stat().st_mtime > built_mtime:
            return True
    return False


def _ensure_build() -> None:
    if CLAIM.exists() and FIXTURE_PUBLIC.exists() and not _claim_sources_newer_than_build():
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


def test_claim_page_has_required_fields_and_email_only_cta(built):
    html = CLAIM.read_text(encoding="utf-8")
    assert 'id="listing-claim-form"' in html or "id=listing-claim-form" in html
    for name in (
        "name",
        "listing_id",
        "listing_url",
        "claimant_name",
        "claimant_email",
        "connection",
        "verification",
        "notes",
    ):
        assert f'name="{name}"' in html or f"name={name}" in html
    assert "Send claim by email" in html
    assert "Open GitHub issue" not in html
    assert "Is this your event?" in html
    assert "What happens next" in html
    assert "not shown on the public event page" in html
    assert "/submit/" in html


def test_claim_js_is_mailto_only_with_prefill(built):
    js = CLAIM_JS.read_text(encoding="utf-8")
    assert "Folk Directory claim:" in js
    assert "mailto:" in js
    assert "params.get(\"id\")" in js
    assert "params.get(\"name\")" in js
    assert "params.get(\"url\")" in js
    assert "github" not in js.lower()
    assert "Open GitHub" not in js


def test_no_claim_github_issue_template():
    claim_templates = list(ISSUE_TEMPLATES.glob("*claim*"))
    assert claim_templates == []


def test_claim_not_in_main_nav():
    text = HUGO_TOML.read_text(encoding="utf-8")
    assert 'identifier = "claim"' not in text
    assert 'name = "Claim"' not in text
    assert "[params.claim]" in text


def test_contact_and_about_mention_claim():
    assert "/claim/" in CONTACT.read_text(encoding="utf-8")
    assert "/claim/" in ABOUT.read_text(encoding="utf-8")


def test_fixture_listing_footer_deep_links_claim(built):
    assert FIXTURE_PUBLIC.is_file(), "expected above-the-parapet build output"
    html = FIXTURE_PUBLIC.read_text(encoding="utf-8")
    assert "Claim this listing" in html
    assert "Suggest an update" in html
    assert re.search(r'/claim/\?id=[^"&]+&amp;name=[^"&]+&amp;url=', html) or re.search(
        r'/claim/\?id=[^"&]+&name=[^"&]+&url=', html
    )
