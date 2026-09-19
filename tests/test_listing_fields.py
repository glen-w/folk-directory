"""Field hygiene: when vs body, meta contact dumps, URL-in-when."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingest"))
sys.path.insert(0, str(ROOT / "scripts"))

from listing_fields import (  # noqa: E402
    display_listing_name,
    is_identity_when_stub,
    is_meta_contact_body,
    is_placeholder_name,
    is_thin_body,
    publishable_fields_from_excerpt,
    sanitize_when,
    split_when,
    when_has_url,
    when_looks_like_prose,
)
from scrape_thesession import build_excerpt, first_useful_comment, schedule_when  # noqa: E402


def test_when_has_url_and_website_pointer():
    assert when_has_url("Details on the website: http://example.com/sessions Fridays 9pm")
    assert when_has_url("More details at our website for times")
    assert not when_has_url("Fridays, 9pm to 11pm")


def test_sanitize_when_strips_url_keeps_schedule():
    when = (
        "Details of the sessions are on the website: http://www.androichead.com/sessions "
        "Fridays 9-12: Traditional session. Saturday 2-4: Fireside session."
    )
    schedule, leftover = sanitize_when(when)
    assert "http" not in schedule.lower()
    assert "website" not in schedule.lower()
    assert "Friday" in schedule or "Fridays" in schedule
    assert "Saturday" in schedule


def test_sanitize_when_splits_schedule_from_prose():
    when = (
        "This session starts on each Saturday at 1pm and finishes at around 3pm. "
        "Suitable for beginners and advanced."
    )
    schedule, leftover = sanitize_when(when)
    assert "Saturday" in schedule
    assert "1pm" in schedule or "1 pm" in schedule.lower() or "13:00" in schedule
    assert "beginners" in leftover.lower()


def test_sanitize_when_moves_pure_prose_to_leftover():
    when = "Imagine an old thatched coaching Inn, down a secluded leafy lane."
    schedule, leftover = sanitize_when(when)
    assert schedule == ""
    assert "thatched" in leftover


def test_is_meta_contact_body_pipe_line():
    body = "Belfast | Antrim | Northern Ireland | tel 028 9031 2582 | hello@x.com | @54.60005,-5.92840"
    assert is_meta_contact_body(body)
    assert is_thin_body(body)


def test_is_meta_contact_body_rejects_real_blurb():
    body = "A friendly open session. All musicians welcome.\n\n@54.60005,-5.92840"
    assert not is_meta_contact_body(body)


def test_publishable_fields_from_excerpt_rejects_pipe_meta():
    excerpt = "Belfast | Antrim | Northern Ireland | tel 028 9031 2582 | hello@x.com"
    when = "Great music - hosts are Maria (Flute). Visiting musicians welcome about 9."
    fields = publishable_fields_from_excerpt(
        excerpt,
        when=when,
        name="White's Tavern",
        place="Belfast",
    )
    assert "tel" not in fields["body"].lower()
    assert "|" not in fields["body"]
    assert "Maria" in fields["body"] or fields["when"] == ""
    assert fields["email"] == "hello@x.com"
    assert fields["address"].startswith("@54") is False  # no coords in excerpt without @ pair here


def test_publishable_fields_promotes_email_and_coords_not_address_pin():
    excerpt = "Belfast | Antrim | Northern Ireland | tel 028 | hello@whitestavernbelfast.com | @54.60005,-5.92840"
    fields = publishable_fields_from_excerpt(
        excerpt,
        when="Every Friday from 9pm.",
        name="White's Tavern",
    )
    assert fields["email"] == "hello@whitestavernbelfast.com"
    assert fields["address"] == ""
    assert fields["coordinates"] == {"lat": 54.60005, "lng": -5.92840}
    assert "Friday" in fields["when"]
    assert "tel" not in fields["body"].lower()


def test_thesession_schedule_when_ignores_comments():
    detail = {
        "schedule": ["Thu · 21:00"],
        "comments": [{"content": "Great music - hosts are Maria. Come early about 9."}],
    }
    assert schedule_when(detail) == "Weekly, Thursday, 9:00pm"
    assert "Maria" in first_useful_comment(detail)


def test_thesession_schedule_when_empty_without_schedule_lines():
    detail = {"schedule": [], "comments": [{"content": "Friendly session every Friday."}]}
    assert schedule_when(detail) == ""
    assert "Friendly" in build_excerpt(
        town="Belfast",
        area="Antrim",
        country="Northern Ireland",
        venue={},
        raw_web="",
        comment=first_useful_comment(detail),
    )


def test_when_looks_like_prose():
    assert when_looks_like_prose("Landlord and landlady very welcoming! Good venue for session.")
    assert not when_looks_like_prose("Every Wednesday, 7pm to 9pm.")


def test_split_when_dirty_onion_timetable():
    when = (
        "Friday, 9pm - 12pm. Saturday afternoon, 2pm - 4pm. "
        "Saturday evening, 9pm - 12pm. Sunday afternoon, 2pm - 5pm."
    )
    schedule, leftover, _ = split_when(when)
    assert leftover == ""
    assert "Friday" in schedule and "Sunday" in schedule


def test_placeholder_names_detected():
    assert is_placeholder_name("Listing 411")
    assert is_placeholder_name("listing-22")
    assert is_placeholder_name("Unknown")
    assert is_placeholder_name("Session")
    assert is_placeholder_name("")
    assert not is_placeholder_name("Session at The Bugle")
    assert not is_placeholder_name("The Bugle")


def test_display_listing_name_from_venue():
    assert (
        display_listing_name(
            name="Listing 411",
            venue="The Bugle",
            event_types=["session"],
            place="Botley",
        )
        == "Session at The Bugle"
    )
    assert (
        display_listing_name(
            name="Listing 22",
            venue="The Kitchen Garden Cafe",
            event_types=["folk-club"],
        )
        == "Folk Club at The Kitchen Garden Cafe"
    )
    assert (
        display_listing_name(name="White's Tavern", venue="White's Tavern")
        == "White's Tavern"
    )


def test_publishable_stub_does_not_echo_listing_id():
    fields = publishable_fields_from_excerpt(
        "Index: stub",
        when="First Tuesdays, 8.00pm",
        name="Listing 411",
        venue="The Bugle",
        place="Botley",
    )
    # Empty/meta excerpts use leftover schedule prose — Index: prefix is not
    # handled here; assert the shared display_name helper is what publish uses.
    assert display_listing_name(
        name="Listing 411", venue="The Bugle", event_types=["session"]
    ) == "Session at The Bugle"
    assert fields["body"] == ""
    thin = publishable_fields_from_excerpt(
        "",
        when="First Tuesdays, 8.00pm. Friendly open session.",
        name="Listing 411",
        venue="The Bugle",
        place="Botley",
    )
    assert "Listing 411" not in thin["body"]
    assert "Friendly" in thin["body"] or "Bugle" in thin["body"] or thin["when"]


def test_identity_when_stub_detected():
    assert is_identity_when_stub(
        "Anglers Folk Night takes place at Anglers Rest, Bamford, on the first Sunday of the month.",
        name="Anglers Folk Night",
        venue="Anglers Rest, Bamford",
        place="Bamford",
    )
    assert is_identity_when_stub(
        "The Roost at The Roost (Maynooth) — Friday, Every Week",
        name="The Roost",
        venue="The Roost",
        place="Maynooth",
    )
    assert not is_identity_when_stub(
        "All musicians welcome.",
        name="Eileen's Bar",
        venue="Eileen's Bar",
        place="Aghamore Village",
    )


def test_publishable_fields_does_not_fabricate_identity_stub():
    stub = publishable_fields_from_excerpt(
        "The Roost at The Roost (Maynooth) — Friday, Every Week",
        when="Friday, Every Week",
        name="The Roost",
        venue="The Roost",
        place="Maynooth",
    )
    assert stub["body"] == ""
    real = publishable_fields_from_excerpt(
        "Nice atmosphere.",
        when="Fridays, 9pm",
        name="The Roost",
        venue="The Roost",
        place="Maynooth",
    )
    assert "atmosphere" in real["body"].lower()
    assert "Maynooth" not in real["body"]
