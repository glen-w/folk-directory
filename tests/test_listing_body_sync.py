from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "ingest"))

from listing_body_sync import (  # noqa: E402
    extract_primary_location,
    extract_schedule,
    location_updates,
    should_restore_body,
    text_matches_listing,
)


WALLASEY_FM = {
    "name": "Wallasey Folk & Acoustic Club",
    "title": "Wallasey Folk & Acoustic Club",
    "venue": "Misty Blues",
    "address": "Manor Road, Liscard",
    "place": "Wallasey",
    "post_code": "CH44 1BY",
    "when": "Monthly, 1st & 3rd Sunday",
    "event_types": ["folk-club"],
}
WALLASEY_BODY = (
    "Wallasey Folk & Acoustic Club meets on the first Saturday of every month "
    "at Café UniTea, 100 Liscard Road, CH44 0AA. Doors open at 7pm, with a "
    "7.30pm start and a finish by 10pm at the latest. Entry is free."
)


def test_extract_wallasey_location():
    loc = extract_primary_location(WALLASEY_BODY)
    assert loc["post_code"] == "CH44 0AA"
    assert "Liscard" in loc["address"]
    assert "UniTea" in loc["venue"] or "Unitea" in loc["venue"] or "Cafe" in loc["venue"]


def test_extract_wallasey_schedule():
    when = extract_schedule(WALLASEY_BODY)
    assert "Saturday" in when
    assert "1st" in when or "First" in when
    assert "Sunday" not in when


def test_location_updates_wallasey():
    updates = location_updates(WALLASEY_FM, WALLASEY_BODY)
    assert updates["post_code"] == "CH44 0AA"
    assert updates["venue"]
    assert "Misty" not in updates["venue"]
    assert "Liscard Road" in updates["address"]
    assert "Saturday" in updates["when"]


def test_identity_same_club():
    ok, why = text_matches_listing(WALLASEY_BODY, WALLASEY_FM)
    assert ok, why


def test_identity_rejects_other_club():
    fm = {
        "name": "The Errigle Inn",
        "venue": "The Errigle Inn",
        "place": "Belfast",
    }
    body = (
        "Bingham Folk Club is a friendly club. Club nights are held monthly "
        "at the Bingham Rugby Club Pavilion, NG13 8TN."
    )
    ok, why = text_matches_listing(body, fm)
    assert not ok
    assert why.startswith("rival:")


def test_identity_allows_club_named_for_the_pub():
    fm = {
        "name": "The Elephant & Castle",
        "venue": "Elephant and Castle",
        "place": "Lewes",
    }
    body = (
        "The Lewes Saturday Folk Club meets every Saturday evening. "
        "The club meets at The Elephant & Castle in Lewes."
    )
    ok, why = text_matches_listing(body, fm)
    assert ok, why


def test_identity_rejects_hub_rewrite():
    fm = {
        "name": "Folk At THe Club",
        "venue": "Churchdown Club",
        "place": "Churchdown",
    }
    body = (
        "Now in its fifth decade, Topsham Folk Club is one of the most vibrant "
        "clubs. Monthly concerts take place at Matthews Hall, Topsham."
    )
    ok, why = text_matches_listing(body, fm)
    assert not ok, why


def test_restore_unusable_and_rival():
    assert should_restore_body({"name": "Lavery's", "venue": "Lavery's"}, "[no output]", applied_www=True)[0]
    fm = {"name": "The Errigle Inn", "venue": "The Errigle Inn", "place": "Belfast"}
    body = "Bingham Folk Club is a friendly club at the pavilion, NG13 8TN."
    assert should_restore_body(fm, body, applied_www=True)[0]


def test_keep_rebrand_haverfolk():
    fm = {
        "name": "Havering Folk Club",
        "venue": "The White Horse",
        "place": "Romford",
        "event_types": ["folk-club"],
    }
    body = "HaverFolk - The Feelgood Folk Club!\n\nWe have an open session every Wednesday."
    assert not should_restore_body(fm, body, applied_www=True)[0]


def test_keep_generic_club_body_without_other_venue():
    fm = {
        "name": "Faversham Folk Club",
        "venue": "The Chimney Boy",
        "place": "Faversham",
        "post_code": "ME13 8PG",
    }
    body = "The club room is upstairs. The club welcomes all visitors."
    assert not should_restore_body(fm, body, applied_www=True)[0]


def test_no_sync_when_identity_fails():
    fm = {
        "name": "The Beehive",
        "venue": "Harthill Village Hall",
        "place": "Harthill",
        "post_code": "S26 7YL",
        "event_types": ["folk-club"],
    }
    body = (
        "Cottingham Live Acoustic Music Club meets each Wednesday night at "
        "The BackRoom, 173 Hallgate, Cottingham HU16 4BB."
    )
    assert location_updates(fm, body) == {}
