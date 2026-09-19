"""Venue-name address matching. No Nominatim calls."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "ingest"))

import venue_address as va  # noqa: E402


def test_search_queries_try_name_without_possessive_type():
    queries = va._search_queries("Bill Chawke's Bar", "Adare", "Limerick", "Ireland")
    assert queries[0] == "Bill Chawke's Bar, Adare"
    assert "Bill Chawke, Adare" in queries
    assert all("Limerick" not in q and "Ireland" not in q for q in queries)


def test_route_ref_is_not_a_street():
    assert va.street_from_nominatim({"road": "R459"}) == ""
    assert va.street_from_nominatim({"road": "N21"}) == ""
    assert va.street_from_nominatim({"house_number": "17", "road": "Parnell Street"}) == "17 Parnell Street"


def test_names_match_possessive_and_reject_longer_neighbour():
    assert va.names_match("Bill Chawke's Bar", "Bill Chawke")
    assert va.names_match("The Park Bar", "The Park Bar")
    assert not va.names_match("The Park Bar", "Phoenix Park")
    assert va.names_match("Sin É", "Sin E")
    assert not va.names_match("The Duke", "The Duke of York")
    assert not va.names_match("Charlie's", "Charlie Ville")
    assert not va.names_match("St John's", "Ballinteer St John's GAA Club")
    assert va.names_match("Franciscan Well", "Franciscan Well Brew Pub")
    assert va.names_match("Cultúrlann", "Cultúrlann McAdam Ó Fiaich")
    assert va.names_match("Cromore Halt", "Cromore Halt Restaurant and B&B")


def test_pick_named_venue_not_nearest_shop():
    results = [
        {
            "lat": "52.56190",
            "lon": "-8.79300",
            "category": "shop",
            "type": "convenience",
            "name": "Gala",
            "address": {"road": "Main Street", "house_number": "1", "postcode": "V94 F4E2"},
        },
        {
            "lat": "52.5632898",
            "lon": "-8.7925603",
            "category": "amenity",
            "type": "pub",
            "name": "Bill Chawke",
            "address": {
                "amenity": "Bill Chawke",
                "road": "Rathkeale Road",
                "postcode": "V94 CX37",
                "village": "Adare",
            },
        },
    ]
    hit = va.pick_venue_address("Bill Chawke's Bar", 52.56187, -8.79299, results)
    assert hit is not None
    assert hit["address"] == "Rathkeale Road"
    assert hit["post_code"] == "V94 CX37"
    assert hit["matched_name"] == "Bill Chawke"


def test_pick_includes_house_number_and_uk_postcode():
    results = [
        {
            "lat": "55.95000",
            "lon": "-3.19000",
            "category": "amenity",
            "type": "pub",
            "name": "White Hart Inn",
            "address": {
                "house_number": "34",
                "road": "Grassmarket",
                "postcode": "EH1 2JU",
            },
        }
    ]
    hit = va.pick_venue_address("White Hart Inn", 55.95010, -3.19010, results)
    assert hit is not None
    assert hit["address"] == "34 Grassmarket"
    assert hit["post_code"] == "EH1 2JU"


def test_pick_rejects_far_namesake_and_highway():
    far = [
        {
            "lat": "53.3498",
            "lon": "-6.2603",
            "category": "amenity",
            "name": "The Cobblestone",
            "address": {"road": "King Street", "postcode": "D07 YX00"},
        }
    ]
    assert va.pick_venue_address("The Cobblestone", 53.2700, -9.0500, far) is None
    highway = [
        {
            "lat": "52.56187",
            "lon": "-8.79299",
            "category": "highway",
            "type": "residential",
            "name": "Rathkeale Road",
            "address": {"road": "Rathkeale Road"},
        }
    ]
    assert va.pick_venue_address("Bill Chawke's Bar", 52.56187, -8.79299, highway) is None


def test_front_matter_field_keeps_body():
    text = "---\naddress: ''\npost_code: ''\nstatus: listed\n---\n\nStill here.\n"
    out = va.set_front_matter_field(text, "address", "St. Mary's Road")
    out = va.set_front_matter_field(out, "post_code", "V94 CX37")
    assert 'address: "St. Mary\'s Road"' in out
    assert "post_code: V94 CX37" in out
    assert out.endswith("---\n\nStill here.\n")
    assert "status: listed" in out


def test_merge_cached_street_fills_gaps_only(monkeypatch, tmp_path):
    cache_path = tmp_path / "cache.json"
    monkeypatch.setattr(va, "CACHE_PATH", cache_path)
    monkeypatch.setattr(va, "_CACHE", None)
    va.save_cache(
        {
            "entries": {
                va.cache_key("Doolin Inn", 53.01262, -9.38377): {
                    "ok": True,
                    "address": "Fisher Street",
                    "post_code": "V95 RX23",
                }
            }
        }
    )
    monkeypatch.setattr(va, "_CACHE", None)
    street, pc = va.merge_cached_street(
        "",
        "",
        venue="Doolin Inn",
        lat=53.01262,
        lng=-9.38377,
    )
    assert street == "Fisher Street"
    assert pc == "V95 RX23"
    street, pc = va.merge_cached_street(
        "Already Street",
        "V95 A1B2",
        venue="Doolin Inn",
        lat=53.01262,
        lng=-9.38377,
    )
    assert street == "Already Street"
    assert pc == "V95 A1B2"
