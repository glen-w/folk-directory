"""Compact session when normalisation: Thursday, 21:00."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingest"))

from common import normalize_session_when, normalize_when, observation  # noqa: E402


def test_expand_abbrev_and_middle_dot():
    assert normalize_session_when("Thu · 21:00") == "Thursday, 21:00"
    assert normalize_session_when("Fri · 21:30") == "Friday, 21:30"
    assert normalize_session_when("Mon · 9:00") == "Monday, 09:00"


def test_dedupe_full_and_abbrev():
    assert normalize_session_when("Sunday 21:30; Sun · 21:30") == "Sunday, 21:30"
    assert (
        normalize_session_when(
            "Wednesday 21:30; Thursday 21:30; Friday 21:30; Wed · 21:30; Thu · 21:30; Fri · 21:30"
        )
        == "Wednesday, 21:30; Thursday, 21:30; Friday, 21:30"
    )


def test_multi_night():
    assert normalize_session_when("Wed · 22:00; Thu · 21:30") == "Wednesday, 22:00; Thursday, 21:30"


def test_leaves_prose_alone():
    prose = "Every Thursday from 8pm onward, mostly Scottish and Irish trad"
    assert normalize_session_when(prose) == prose
    assert normalize_session_when("Thursday, Every Week") == "Thursday, Every Week"
    assert normalize_session_when("Wednesdays, 8pm-10pm.") == "Wednesdays, 8pm-10pm."
    # Do not collapse internal whitespace on narrative when fields
    narrative = "Good venue.  It has  two spaces."
    assert normalize_session_when(narrative) == narrative


def test_festival_path_unchanged_by_session_helper():
    assert normalize_when("15–17 August 2026", event_kind="festival") == "August"
    assert normalize_when("Thu · 21:00", event_kind="session") == "Thursday, 21:00"


def test_observation_normalises_session_when():
    row = observation(
        name="Baker's Bar",
        source="seshie",
        source_url="https://sesh.ie/",
        event_kind="session",
        when="Thu · 21:00",
    )
    assert row["when"] == "Thursday, 21:00"
