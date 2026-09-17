"""Unit tests for map geocoding helpers (no Nominatim network calls)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import geocode_listings as g  # noqa: E402


def test_extract_body_coordinates_at_form():
    text = """---
title: Ben Nevis
---

Glasgow | Scotland | tel 0141 576 5204 | @55.86483,-4.28514
"""
    assert g.extract_body_coordinates(text) == {"lat": 55.86483, "lng": -4.28514}


def test_extract_body_coordinates_labeled():
    text = """---
title: X
---

Belfast. Coordinates: 54.60848, -5.92005.
"""
    assert g.extract_body_coordinates(text) == {"lat": 54.60848, "lng": -5.92005}


def test_extract_body_coordinates_rejects_out_of_range():
    text = "Somewhere @12.34567,100.00000"
    assert g.extract_body_coordinates(text) is None


def test_build_address_venue_place():
    addr = g.build_address(
        {"venue": "Ben Nevis", "place": "Glasgow", "county": "Glasgow", "address": ""}
    )
    # Identical place/county fragments are deduped.
    assert addr == "Ben Nevis, Glasgow, United Kingdom"


def test_fallback_queries_include_street_without_club_name():
    data = {
        "venue": "The Star",
        "address": "The Admiral, Waterloo Street",
        "place": "Glasgow",
        "county": "Glasgow",
    }
    address = g.build_address(data)
    queries = g.fallback_queries(data, address)
    assert "The Admiral, Waterloo Street, Glasgow, United Kingdom" in queries
    # Street-only query should come before bare city fallback.
    street_i = queries.index("The Admiral, Waterloo Street, Glasgow, United Kingdom")
    city_i = queries.index("Glasgow, United Kingdom")
    assert street_i < city_i
