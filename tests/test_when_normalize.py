"""Cadence-first session when normalisation: Monthly, 2nd Friday, 9:00pm."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingest"))
sys.path.insert(0, str(ROOT / "scripts"))

from common import normalize_session_when, normalize_when, observation  # noqa: E402
from listing_fields import sanitize_when  # noqa: E402
from when_format import standardize_schedule_when  # noqa: E402
import rewrite_listing_bodies as rw  # noqa: E402


def _ids(pairs: list[tuple[str, str]]) -> list[str]:
    return [orig[:70] for orig, _ in pairs]


REWRITE_CASES = [
    # User example + filler / late
    (
        "Takes place every month on the 2nd Friday at 9:00 pm - Late",
        "Monthly, 2nd Friday, 9:00pm",
    ),
    # Compact sesh.ie / thesession
    ("Thu · 21:00", "Weekly, Thursday, 9:00pm"),
    ("Fri · 21:30", "Weekly, Friday, 9:30pm"),
    ("Mon · 9:00", "Weekly, Monday, 9:00am"),
    ("Thursday, 21:00", "Weekly, Thursday, 9:00pm"),
    ("Friday, 21:30", "Weekly, Friday, 9:30pm"),
    ("Sun · 00:00", "Weekly, Sunday, 12:00am"),
    ("Sun · 12:00", "Weekly, Sunday, 12:00pm"),
    ("Daily · 21:00", "Nightly, 9:00pm"),
    ("Nightly · 21:30", "Nightly, 9:30pm"),
    # Dedupe merge artefacts
    ("Sunday 21:30; Sun · 21:30", "Weekly, Sunday, 9:30pm"),
    (
        "Wednesday 21:30; Thursday 21:30; Friday 21:30; Wed · 21:30; Thu · 21:30; Fri · 21:30",
        "Weekly, Wednesday & Thursday & Friday, 9:30pm",
    ),
    (
        "Wed · 22:00; Thu · 21:30",
        "Weekly, Wednesday, 10:00pm; Thursday, 9:30pm",
    ),
    # Legacy "Day, Every Week" / "in Month"
    ("Thursday, Every Week", "Weekly, Thursday"),
    ("Wednesday, 1st in Month", "Monthly, 1st Wednesday"),
    ("Sunday, 1st & 3rd", "Monthly, 1st & 3rd Sunday"),
    ("Wednesday, 1st & 3rd in Month", "Monthly, 1st & 3rd Wednesday"),
    ("Thursday, Last in month", "Monthly, Last Thursday"),
    ("Thursday, Last in Month", "Monthly, Last Thursday"),
    ("Thursday, Every 2 weeks", "Fortnightly, Thursday"),
    ("Thursday, fortnightly", "Fortnightly, Thursday"),
    ("Wednesday, 2nd & 4th", "Monthly, 2nd & 4th Wednesday"),
    ("Friday, 4th", "Monthly, 4th Friday"),
    # Ordinal + month prose
    ("First Friday, 8.30pm", "Monthly, 1st Friday, 8:30pm"),
    ("First Tuesdays, 8.00pm", "Monthly, 1st Tuesday, 8:00pm"),
    ("2nd Tuesday every month", "Monthly, 2nd Tuesday"),
    ("1st Thursday of every month", "Monthly, 1st Thursday"),
    ("Second Friday of each month", "Monthly, 2nd Friday"),
    ("First Tuesday of the month", "Monthly, 1st Tuesday"),
    ("Third Wednesday of the Month", "Monthly, 3rd Wednesday"),
    ("Third Fridays, 8pm-late", "Monthly, 3rd Friday, 8:00pm"),
    ("2nd and 4th Thursday of each month", "Monthly, 2nd & 4th Thursday"),
    ("2nd & 4th Thursday of each Month", "Monthly, 2nd & 4th Thursday"),
    (
        "Last Friday of the month, 2000 - 2330",
        "Monthly, Last Friday, 8:00pm-11:30pm",
    ),
    (
        "First and Third Wednesday of the month, 8.45 - 11.00pm",
        "Monthly, 1st & 3rd Wednesday, 8:45pm-11:00pm",
    ),
    (
        "Last Monday of every month, starts at 9pm",
        "Monthly, Last Monday, 9:00pm",
    ),
    ("Sessions held on the first Saturday of every month.", "Monthly, 1st Saturday"),
    # Fortnightly "every second" vs monthly "2nd of the month"
    ("every second Wednesday", "Fortnightly, Wednesday"),
    ("every other Friday", "Fortnightly, Friday"),
    ("every second Friday of the month", "Monthly, 2nd Friday"),
    # Weekly prose + clocks
    ("Wednesdays, 8pm-10pm.", "Weekly, Wednesday, 8:00pm-10:00pm"),
    ("Every Thursday at 8pm", "Weekly, Thursday, 8:00pm"),
    ("Every Thursday from 8pm to 10pm", "Weekly, Thursday, 8:00pm-10:00pm"),
    ("Every Friday from around 21.30", "Weekly, Friday, 9:30pm"),
    ("Every Sunday from 8.00 pm", "Weekly, Sunday, 8:00pm"),
    ("Session on Tuesdays at 6pm.", "Weekly, Tuesday, 6:00pm"),
    ("Held on Wednesday nights at around 9pm.", "Weekly, Wednesday, 9:00pm"),
    (
        "Sessions on Thursdays and Sundays at 9pm.",
        "Weekly, Thursday & Sunday, 9:00pm",
    ),
    (
        "Sessions at around 9pm on Wednesdays, Fridays, Saturdays, and Sundays.",
        "Weekly, Wednesday & Friday & Saturday & Sunday, 9:00pm",
    ),
]


LEAVE_ALONE_CASES = [
    "Friday",
    "Fridays",
    "July",
    "15–17 August 2026",
    "Thursday, Other",
    "Thursday, Variable",
    "Varied, Every Week",
    "Wednesdays, 8pm-10",  # end hour with no meridian
    "Thursday, 21:00; extra notes here",
    "Every Thursday from 8pm onward, mostly Scottish and Irish trad",
    "Good venue.  It has  two spaces.",
    (
        "Open trad session 1st and 3rd Friday hosted by Sult na Sollán "
        "every month 9.30-Late."
    ),
    "Every second Saturday from 9pm. Every Sunday from 7pm.",
    "Tuesday of each month from 8pm in the back room",
    "Weekly Trad Session every Thursday evening from 21:30 Musicians Welcome!",
]


IDEMPOTENT_CASES = [
    "Monthly, 2nd Friday, 9:00pm",
    "Weekly, Thursday",
    "Weekly, Thursday, 9:00pm",
    "Fortnightly, Thursday",
    "Nightly, 9:30pm",
    "Monthly, 1st & 3rd Sunday",
    "Monthly, Last Thursday",
    "Monthly, Last Friday, 8:00pm-11:30pm",
    "Weekly, Wednesday, 10:00pm; Thursday, 9:30pm",
    "Weekly, Wednesday & Thursday & Friday, 9:30pm",
]


@pytest.mark.parametrize("original, expected", REWRITE_CASES, ids=_ids(REWRITE_CASES))
def test_standardize_schedule_when_rewrites(original: str, expected: str) -> None:
    assert standardize_schedule_when(original) == expected
    assert normalize_session_when(original) == expected


@pytest.mark.parametrize("original", LEAVE_ALONE_CASES)
def test_standardize_schedule_when_leaves_uncertain_values(original: str) -> None:
    assert standardize_schedule_when(original) == original
    assert normalize_session_when(original) == original


@pytest.mark.parametrize("canonical", IDEMPOTENT_CASES)
def test_standardize_schedule_when_is_idempotent(canonical: str) -> None:
    once = standardize_schedule_when(canonical)
    assert once == canonical
    assert standardize_schedule_when(once) == canonical


def test_empty_and_whitespace():
    assert standardize_schedule_when("") == ""
    assert standardize_schedule_when("   ") == ""
    assert normalize_session_when("") == ""
    assert normalize_when("", event_kind="session") == ""
    assert normalize_when("", event_kind="festival") == ""


def test_does_not_collapse_narrative_whitespace():
    narrative = "Good venue.  It has  two spaces."
    assert standardize_schedule_when(narrative) == narrative


def test_long_prose_is_left_alone():
    long_prose = (
        "This is a friendly mixed session with a house band and visiting players "
        "who drop in after gigs, usually sometime in the evening when everyone is ready."
    )
    assert len(long_prose) > 140
    assert standardize_schedule_when(long_prose) == long_prose


def test_festival_path_month_only():
    assert normalize_when("15–17 August 2026", event_kind="festival") == "August"
    assert normalize_when("April / May", event_kind="festival") == "April / May"
    assert normalize_when("Thu · 21:00", event_kind="session") == "Weekly, Thursday, 9:00pm"
    # Session helper must not month-strip festival-looking dates
    assert standardize_schedule_when("15–17 August 2026") == "15–17 August 2026"


def test_observation_normalises_compact_and_monthly():
    compact = observation(
        name="Baker's Bar",
        source="seshie",
        source_url="https://sesh.ie/",
        event_kind="session",
        when="Thu · 21:00",
    )
    assert compact["when"] == "Weekly, Thursday, 9:00pm"

    monthly = observation(
        name="An Grianán Hotel",
        source="seshie",
        source_url="https://sesh.ie/",
        event_kind="session",
        when="Takes place every month on the 2nd Friday at 9:00 pm - Late",
    )
    assert monthly["when"] == "Monthly, 2nd Friday, 9:00pm"


def test_real_listing_files_match_expected_when():
    listings = ROOT / "content" / "listings"
    expected = {
        "an-grian-n-hotel.md": (
            "Monthly, 2nd Friday, 9:00pm",
            "Monthly, 2nd Friday, 9:00pm",
        ),
        "baker-s-bar.md": ("Thursday, 21:00", "Weekly, Thursday, 9:00pm"),
        "edinburgh-folk-club.md": ("Weekly, Wednesday", "Weekly, Wednesday"),
        "hexham-gathering.md": ("May", "May"),
    }
    for name, (orig, new) in expected.items():
        path = listings / name
        text = path.read_text(encoding="utf-8")
        fm_raw, _ = rw.split_listing(text)
        got_orig, got_new = rw.standardised_when(fm_raw)
        assert got_orig == orig, name
        assert got_new == new, name
    schedule, leftover = sanitize_when(
        "Takes place every month on the 2nd Friday at 9:00 pm - Late"
    )
    assert leftover == ""
    assert standardize_schedule_when(schedule) == "Monthly, 2nd Friday, 9:00pm"


def test_rewrite_script_standardised_when_session_and_festival():
    session_fm = (
        "\nname: An Grianán Hotel\nevent_types:\n- session\n"
        "when: Takes place every month on the 2nd Friday at 9:00 pm - Late\n"
    )
    orig, new = rw.standardised_when(session_fm)
    assert orig == "Takes place every month on the 2nd Friday at 9:00 pm - Late"
    assert new == "Monthly, 2nd Friday, 9:00pm"

    festival_fm = "\nname: Hexham Gathering\nevent_types:\n- festival\nwhen: 15–17 August 2026\n"
    orig, new = rw.standardised_when(festival_fm)
    assert orig == "15–17 August 2026"
    assert new == "August"

    empty_fm = "\nname: Stub\nevent_types:\n- session\n"
    assert rw.standardised_when(empty_fm) == ("", "")


def test_replace_when_in_fm_preserves_other_fields():
    fm = (
        "\ntitle: An Grianán Hotel\n"
        "event_types:\n- session\n"
        "when: Takes place every month on the 2nd Friday at 9:00 pm - Late\n"
        "www: www.angriananhotel.com\n"
    )
    out = rw.replace_when_in_fm(fm, "Monthly, 2nd Friday, 9:00pm")
    assert "when: Monthly, 2nd Friday, 9:00pm\n" in out
    assert "www: www.angriananhotel.com" in out
    assert "title: An Grianán Hotel" in out
    assert "Takes place" not in out


def test_process_one_when_only_skip_review_would_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    listing = tmp_path / "an-grian-n-hotel.md"
    listing.write_text(
        "---\n"
        "title: An Grianán Hotel\n"
        "event_types:\n- session\n"
        "when: Takes place every month on the 2nd Friday at 9:00 pm - Late\n"
        "---\n\n"
        "Session in the Fort Bar.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(rw, "ROOT", tmp_path)
    row = rw.process_one(
        listing,
        rewrite_model="unused",
        review_model="unused",
        base_url="http://localhost:9",
        rewrite_system="",
        review_system="",
        when_review_system="",
        timeout=1.0,
        apply=True,
        include_revise=False,
        min_chars=1,
        when_only=True,
        skip_when_review=True,
    )
    assert row["when"] == "Monthly, 2nd Friday, 9:00pm"
    assert row["when_changed"] is True
    assert row["would_apply_when"] is True
    assert row["applied_when"] is True
    written = listing.read_text(encoding="utf-8")
    assert "when: Monthly, 2nd Friday, 9:00pm" in written
    assert "Session in the Fort Bar." in written


def test_process_one_when_only_rejected_review_keeps_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    listing = tmp_path / "demo.md"
    listing.write_text(
        "---\n"
        "title: Demo\n"
        "event_types:\n- session\n"
        "when: Thursday, Every Week\n"
        "---\n\n"
        "A club.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(rw, "ROOT", tmp_path)

    def _reject(**_kwargs):
        return {
            "verdict": "reject",
            "detail_loss": "major",
            "invention": "major",
            "tone_ok": False,
            "issues": ["nope"],
            "notes": "keep original",
        }

    monkeypatch.setattr(rw, "call_when_review", _reject)
    row = rw.process_one(
        listing,
        rewrite_model="unused",
        review_model="unused",
        base_url="http://localhost:9",
        rewrite_system="",
        review_system="",
        when_review_system="review",
        timeout=1.0,
        apply=True,
        include_revise=False,
        min_chars=1,
        when_only=True,
        skip_when_review=False,
    )
    assert row["when"] == "Weekly, Thursday"
    assert row["would_apply_when"] is False
    assert row["applied_when"] is False
    assert "when: Thursday, Every Week" in listing.read_text(encoding="utf-8")
