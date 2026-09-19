"""Cadence-first session when normalisation: Monthly, 2nd Friday, 9:00pm."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingest"))

from common import normalize_session_when, normalize_when, observation  # noqa: E402
from when_format import standardize_schedule_when  # noqa: E402


def test_example_takes_place_monthly():
    assert (
        standardize_schedule_when(
            "Takes place every month on the 2nd Friday at 9:00 pm - Late"
        )
        == "Monthly, 2nd Friday, 9:00pm"
    )


def test_expand_abbrev_and_middle_dot():
    assert normalize_session_when("Thu · 21:00") == "Weekly, Thursday, 9:00pm"
    assert normalize_session_when("Fri · 21:30") == "Weekly, Friday, 9:30pm"
    assert normalize_session_when("Mon · 9:00") == "Weekly, Monday, 9:00am"


def test_dedupe_full_and_abbrev():
    assert normalize_session_when("Sunday 21:30; Sun · 21:30") == "Weekly, Sunday, 9:30pm"
    assert (
        normalize_session_when(
            "Wednesday 21:30; Thursday 21:30; Friday 21:30; Wed · 21:30; Thu · 21:30; Fri · 21:30"
        )
        == "Weekly, Wednesday & Thursday & Friday, 9:30pm"
    )


def test_multi_night():
    assert (
        normalize_session_when("Wed · 22:00; Thu · 21:30")
        == "Weekly, Wednesday, 10:00pm; Thursday, 9:30pm"
    )


def test_every_week_and_in_month():
    assert normalize_session_when("Thursday, Every Week") == "Weekly, Thursday"
    assert normalize_session_when("Wednesday, 1st in Month") == "Monthly, 1st Wednesday"
    assert normalize_session_when("Sunday, 1st & 3rd") == "Monthly, 1st & 3rd Sunday"
    assert normalize_session_when("Thursday, Last in month") == "Monthly, Last Thursday"
    assert normalize_session_when("Thursday, Every 2 weeks") == "Fortnightly, Thursday"


def test_ordinal_month_prose():
    assert (
        normalize_session_when("First Friday, 8.30pm") == "Monthly, 1st Friday, 8:30pm"
    )
    assert normalize_session_when("2nd Tuesday every month") == "Monthly, 2nd Tuesday"
    assert (
        normalize_session_when("Last Friday of the month, 2000 - 2330")
        == "Monthly, Last Friday, 8:00pm-11:30pm"
    )
    assert (
        normalize_session_when("Wednesdays, 8pm-10pm.")
        == "Weekly, Wednesday, 8:00pm-10:00pm"
    )


def test_nightly_compact():
    assert normalize_session_when("Nightly · 21:30") == "Nightly, 9:30pm"


def test_leaves_prose_alone():
    prose = "Every Thursday from 8pm onward, mostly Scottish and Irish trad"
    assert normalize_session_when(prose) == prose
    narrative = "Good venue.  It has  two spaces."
    assert normalize_session_when(narrative) == narrative
    extra = (
        "Open trad session 1st and 3rd Friday hosted by Sult na Sollán every month 9.30-Late."
    )
    assert normalize_session_when(extra) == extra
    mixed_nights = "Every second Saturday from 9pm. Every Sunday from 7pm."
    assert normalize_session_when(mixed_nights) == mixed_nights


def test_idempotent_canonical():
    canonical = "Monthly, 2nd Friday, 9:00pm"
    assert standardize_schedule_when(canonical) == canonical
    weekly = "Weekly, Thursday, 9:00pm"
    assert standardize_schedule_when(weekly) == weekly


def test_festival_path_unchanged_by_session_helper():
    assert normalize_when("15–17 August 2026", event_kind="festival") == "August"
    assert normalize_when("Thu · 21:00", event_kind="session") == "Weekly, Thursday, 9:00pm"


def test_observation_normalises_session_when():
    row = observation(
        name="Baker's Bar",
        source="seshie",
        source_url="https://sesh.ie/",
        event_kind="session",
        when="Thu · 21:00",
    )
    assert row["when"] == "Weekly, Thursday, 9:00pm"
