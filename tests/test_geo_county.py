"""Unit tests for county / postcode geocode gate (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import geo_county as gc  # noqa: E402
import geocode_listings as g  # noqa: E402
import venue_address as va  # noqa: E402


def test_birmingham_matches_west_midlands():
    assert not gc.postcode_conflicts_listing(
        "West Midlands",
        {"district": "Birmingham", "admin_district": "Birmingham"},
    )


def test_birmingham_conflicts_north_yorkshire():
    assert gc.postcode_conflicts_listing(
        "North Yorkshire",
        {"district": "Birmingham", "admin_district": "Birmingham"},
    )


def test_birmingham_conflicts_south_lanarkshire():
    assert gc.postcode_conflicts_listing(
        "South Lanarkshire",
        {"district": "Birmingham", "admin_district": "Birmingham"},
    )


def test_unresolved_district_is_not_conflict():
    assert not gc.postcode_conflicts_listing(
        "North Yorkshire",
        {"district": "Ryedale-Unknown-XYZ", "admin_district": ""},
    )


def test_town_from_address_when_place_is_county():
    assert gc.town_from_address(
        "136 Westgate, Pickering",
        place="North Yorkshire",
        county="North Yorkshire",
    ) == "Pickering"
    assert gc.town_from_address(
        "St. Ninian's Church Hall, Stonehouse",
        place="South Lanarkshire",
        county="South Lanarkshire",
    ) == "Stonehouse"


def test_is_county_name_not_town():
    assert gc.is_county_name("North Yorkshire")
    assert gc.is_county_name("South Lanarkshire")
    assert gc.is_county_name("West Midlands")
    assert not gc.is_county_name("York")
    assert not gc.is_county_name("Birmingham")
    assert not gc.is_county_name("Pickering")
    assert not gc.is_county_name("Glasgow")
    assert not gc.is_county_name("Edinburgh")


def test_pin_on_centroid():
    pin = {"lat": 52.4819, "lng": -1.89714}
    pc = {"lat": 52.481901, "lng": -1.897143}
    assert gc.pin_on_postcode_centroid(pin, pc)
    assert not gc.pin_on_postcode_centroid(pin, {"lat": 54.25, "lng": -0.78})


def test_trusted_post_code_rejects_birmingham_for_pickering(monkeypatch):
    data = {
        "title": "Pickering Acoustic Music",
        "venue": "The Sun Inn",
        "address": "136 Westgate, Pickering",
        "place": "North Yorkshire",
        "county": "North Yorkshire",
        "post_code": "B2 5HU",
        "lat": 52.4819,
        "lng": -1.89714,
    }

    def fake_meta(pc: str):
        assert "B2" in pc.upper()
        return {
            "latitude": 52.481901,
            "longitude": -1.897143,
            "admin_district": "Birmingham",
            "district": "Birmingham",
            "country": "England",
        }

    monkeypatch.setattr(g, "uk_postcode_meta", fake_meta)
    assert g.trusted_post_code(data) == ""
    assert g.coords_from_listing_postcode(data) is None
    assert "B2" not in g.build_address(data).upper()
    assert "Pickering" in g.build_address(data)
    usable = g.body_coords_usable(data, {"lat": 52.4819, "lng": -1.89714})
    assert usable is None


def test_trusted_post_code_keeps_birmingham_for_good_intent(monkeypatch):
    data = {
        "title": "Folk The Good Intent",
        "venue": "The Good Intent",
        "address": "The Good Intent Great Western. Arcade",
        "place": "Birmingham",
        "county": "West Midlands",
        "post_code": "B2 5HU",
        "lat": 52.4819,
        "lng": -1.89714,
    }

    def fake_meta(pc: str):
        return {
            "latitude": 52.481901,
            "longitude": -1.897143,
            "admin_district": "Birmingham",
            "district": "Birmingham",
            "country": "England",
        }

    monkeypatch.setattr(g, "uk_postcode_meta", fake_meta)
    assert g.trusted_post_code(data) == "B2 5HU"
    assert g.coords_from_listing_postcode(data) == {
        "lat": 52.481901,
        "lng": -1.897143,
    }
    assert "B2 5HU" in g.build_address(data)


def test_matching_postcode_overrides_mismatched_pin(monkeypatch):
    """Trusted postcode still replaces a pin more than 12 km away."""
    data = {
        "title": "Somewhere",
        "venue": "The Pub",
        "address": "High Street",
        "place": "Birmingham",
        "county": "West Midlands",
        "post_code": "B2 5HU",
        "lat": 54.25,
        "lng": -0.78,
    }

    def fake_meta(pc: str):
        return {
            "latitude": 52.481901,
            "longitude": -1.897143,
            "admin_district": "Birmingham",
            "district": "Birmingham",
            "country": "England",
        }

    monkeypatch.setattr(g, "uk_postcode_meta", fake_meta)
    body = {"lat": 54.25, "lng": -0.78}
    pc_pin = g.coords_from_listing_postcode(data)
    assert pc_pin is not None
    assert g._haversine_km(body, pc_pin) > g.PIN_POSTCODE_TOLERANCE_KM
    # body_coords_usable keeps a pin that is NOT on the rejected centroid
    assert g.body_coords_usable(data, body) == body


def test_listing_town_from_address_and_title():
    pickering = {
        "title": "Pickering Acoustic Music",
        "place": "North Yorkshire",
        "address": "136 Westgate, Pickering",
        "county": "North Yorkshire",
    }
    assert g.listing_town(pickering) == "Pickering"
    stonehouse = {
        "title": "Stonehouse Folk Club",
        "place": "South Lanarkshire",
        "address": "St. Ninian's Church Hall, Stonehouse",
        "county": "South Lanarkshire",
    }
    assert g.listing_town(stonehouse) == "Stonehouse"


def test_pick_street_postcode_rejects_county_conflict():
    results = [
        {
            "lat": "52.48",
            "lon": "-1.90",
            "category": "amenity",
            "type": "place_of_worship",
            "addresstype": "amenity",
            "name": "St Ninian's Church Hall",
            "display_name": "St Ninian's Church Hall, Birmingham, B2 5SN",
            "address": {
                "amenity": "St Ninian's Church Hall",
                "city": "Birmingham",
                "county": "West Midlands",
                "postcode": "B2 5SN",
            },
        }
    ]
    assert (
        va.pick_street_postcode(
            "St. Ninian's Church Hall, Stonehouse",
            "Stonehouse",
            results,
            venue="Church Hall",
            county="South Lanarkshire",
        )
        is None
    )


def test_road_matches_rejects_substring_church_hall():
    assert not va._road_matches("Church Hall", "St Ninian's Church Hall")
    assert va._road_matches("Westgate", "Westgate")
    assert va._road_matches("Gallowgate", "121 Gallowgate, Aberdeen")
