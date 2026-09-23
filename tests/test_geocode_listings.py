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


def test_build_address_strips_country_from_street():
    addr = g.build_address(
        {
            "venue": "Blue Lamp",
            "place": "Aberdeen",
            "county": "Aberdeenshire",
            "address": "121 Gallowgate, United Kingdom",
        }
    )
    assert addr == "Blue Lamp, 121 Gallowgate, Aberdeen, Aberdeenshire, United Kingdom"
    assert addr.count("United Kingdom") == 1


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


def test_woolston_place_alias_avoids_basingstoke_street():
    assert g.normalize_place("Woolston") == "Woolston, Southampton"
    data = {"place": "Woolston", "county": "Hampshire"}
    address = g.build_address(data)
    assert "Southampton" in address
    assert "Woolston, Southampton" in g.fallback_queries(data, address)[0] or any(
        "southampton" in q.lower() for q in g.fallback_queries(data, address)
    )


def test_map_www_string_slice_and_empty():
    assert g.map_www({"www": " shipyardrsongwriters.com/gigs "}) == "shipyardrsongwriters.com/gigs"
    assert g.map_www({"www": ["https://example.test", "ignored"]}) == "https://example.test"
    assert g.map_www({"www": ""}) == ""
    assert g.map_www({}) == ""
    assert g.map_www({"www": "''"}) == ""


def test_geocode_no_corpus_id_coord_seeding():
    """Corpus entity ids do not match published listing ids; never seed pins from corpus."""
    assert not hasattr(g, "load_corpus_coords")


def test_coords_from_uk_postcode(monkeypatch):
    g.clear_postcode_meta_cache()

    class Resp:
        status_code = 200
        content = b"{}"

        def raise_for_status(self):
            return None

        @staticmethod
        def json():
            return {"result": {"latitude": 52.45786, "longitude": -2.146676}}

    monkeypatch.setattr(g.requests, "get", lambda *a, **k: Resp())
    hit = g.coords_from_uk_postcode("DY8 1EP")
    assert hit == {"lat": 52.45786, "lng": -2.146676}


def test_coords_from_uk_postcode_uses_terminated_centroid(monkeypatch):
    """Retired codes 404 live but still expose a last-known centroid."""
    g.clear_postcode_meta_cache()

    class Resp:
        status_code = 404
        content = b"{}"

        def raise_for_status(self):
            raise AssertionError("404 should not raise_for_status")

        @staticmethod
        def json():
            return {
                "status": 404,
                "error": "Postcode not found",
                "terminated": {
                    "postcode": "DE1 1YS",
                    "year_terminated": 2015,
                    "latitude": 52.924629,
                    "longitude": -1.48595,
                },
            }

    monkeypatch.setattr(g.requests, "get", lambda *a, **k: Resp())
    hit = g.coords_from_uk_postcode("DE1 1YS")
    assert hit == {"lat": 52.924629, "lng": -1.48595}


def test_coords_from_uk_postcode_404_without_terminated(monkeypatch):
    g.clear_postcode_meta_cache()

    class Resp:
        status_code = 404
        content = b"{}"

        @staticmethod
        def json():
            return {"status": 404, "error": "Invalid postcode"}

    monkeypatch.setattr(g.requests, "get", lambda *a, **k: Resp())
    assert g.coords_from_uk_postcode("DE1 1YS") is None


def test_street_address_drops_country_suffix():
    assert lc.street_address("121 Gallowgate, United Kingdom") == "121 Gallowgate"
    assert lc.street_address("6 Parkgate, UK") == "6 Parkgate"
    assert lc.street_address("11 High Street, Pattingham, U.K.") == "11 High Street, Pattingham"
    assert lc.street_address("United Kingdom") == ""
    assert lc.street_address("Fisher Street") == "Fisher Street"
    street, pin = lc.resolve_street_and_coords(
        "121 Gallowgate, United Kingdom",
        coords={"lat": 57.15000, "lng": -2.09000},
    )
    assert street == "121 Gallowgate"
    assert pin == {"lat": 57.15000, "lng": -2.09000}


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


def test_resolve_coords_tries_street_before_broad_cache(monkeypatch):
    """A poisoned place+county cache must not skip an uncached street query."""
    data = {
        "venue": "Norden Farm Centre for the Arts",
        "address": "Altwood Road",
        "place": "Maidenhead",
        "county": "Berkshire",
    }
    address = g.build_address(data)
    cache = {
        "locations": {
            "maidenhead, berkshire, united kingdom": {
                "address": "Maidenhead, Berkshire, United Kingdom",
                "coordinates": {"lat": 51.4079651, "lng": -1.2830546},
                "geocoded": True,
            }
        }
    }
    calls: list[str] = []

    def fake_geocode(q: str, listing_county: str = ""):
        calls.append(q)
        if "Altwood" in q or "Norden Farm" in q:
            return 51.5155436, -0.7460257
        return None

    monkeypatch.setattr(g, "geocode_query", fake_geocode)
    monkeypatch.setattr(g.time, "sleep", lambda *_a, **_k: None)
    coords, api_called, source = g.resolve_coords(data, address, cache=cache)
    assert api_called
    assert coords == {"lat": 51.5155436, "lng": -0.7460257}
    assert "nominatim:" in source
    assert calls, "expected a live geocode attempt for the street/venue query"
    assert calls[0].lower().startswith("norden farm") or "altwood" in calls[0].lower()
    assert "maidenhead, berkshire" not in calls[0].lower() or "altwood" in calls[0].lower()
