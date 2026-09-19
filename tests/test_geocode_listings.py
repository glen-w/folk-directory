"""Unit tests for map geocoding helpers (no Nominatim network calls)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import geocode_listings as g  # noqa: E402
import listing_coords as lc  # noqa: E402


def test_extract_body_coordinates_from_lat_lng_fields():
    text = """---
title: Jenny Watts
lat: 54.66370
lng: -5.66544
---

"""
    assert g.extract_body_coordinates(text) == {"lat": 54.66370, "lng": -5.66544}


def test_extract_body_coordinates_from_legacy_address_field():
    text = """---
title: Jenny Watts
address: '@54.66370,-5.66544'
---

"""
    assert g.extract_body_coordinates(text) == {"lat": 54.66370, "lng": -5.66544}


def test_extract_body_coordinates_at_form_legacy_body():
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


def test_listing_body_strips_coord_pins():
    text = """---
title: X
---

Friendly open session.

@54.66370,-5.66544
"""
    assert g.listing_body(text) == "Friendly open session."


def test_build_address_skips_coord_pin_address():
    addr = g.build_address(
        {
            "venue": "Jenny Watts",
            "place": "Bangor",
            "county": "Down",
            "address": "@54.66370,-5.66544",
        }
    )
    assert "@54" not in addr
    assert addr == "Jenny Watts, Bangor, Down, United Kingdom"


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


def test_map_www_string_slice_and_empty():
    assert g.map_www({"www": " shipyardrsongwriters.com/gigs "}) == "shipyardrsongwriters.com/gigs"
    assert g.map_www({"www": ["https://example.test", "ignored"]}) == "https://example.test"
    assert g.map_www({"www": ""}) == ""
    assert g.map_www({}) == ""
    assert g.map_www({"www": "''"}) == ""


def test_promote_coords_never_writes_pin_into_address():
    assert (
        lc.promote_coords_to_address(
            "High Street",
            {"lat": 54.66, "lng": -5.66},
        )
        == "High Street"
    )
    assert lc.promote_coords_to_address("", {"lat": 54.66370, "lng": -5.66544}) == ""
    assert lc.promote_coords_to_address("@54.66370,-5.66544", None) == ""
    street, pin = lc.resolve_street_and_coords(
        "@54.66370,-5.66544",
        coords={"lat": 54.66370, "lng": -5.66544},
    )
    assert street == ""
    assert pin == {"lat": 54.66370, "lng": -5.66544}
