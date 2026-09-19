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


def test_yaml_scalar_does_not_quote_comma_addresses():
    """Speech quotes are only for YAML-special characters, not street commas."""
    assert va.yaml_scalar("19 The Ln, Mickleby") == "19 The Ln, Mickleby"
    assert va.yaml_scalar("121 Gallowgate") == "121 Gallowgate"
    assert va.yaml_scalar("St. Mary's Road") == '"St. Mary\'s Road"'
    text = "---\naddress: ''\n---\n\nBody.\n"
    out = va.set_front_matter_field(text, "address", "19 The Ln, Mickleby")
    assert "address: 19 The Ln, Mickleby\n" in out
    assert '"19 The Ln, Mickleby"' not in out


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


def test_observation_drops_pin_splits_postcode_and_uses_cache(monkeypatch, tmp_path):
    """Every scraper goes through observation(); it must not call Nominatim."""
    import common

    monkeypatch.setattr(va, "CACHE_PATH", tmp_path / "cache.json")
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

    def _no_network(*_a, **_k):
        raise AssertionError("observation must not call Nominatim")

    monkeypatch.setattr(va, "lookup_venue_address", _no_network)

    pin_row = common.observation(
        name="Jenny Watts",
        venue="Jenny Watts",
        source="thesession",
        source_url="https://thesession.org/sessions/1",
        event_kind="session",
        place="Bangor",
        address="@54.66370,-5.66544",
        coordinates={"lat": 54.66370, "lng": -5.66544},
    )
    assert "address" not in pin_row
    assert pin_row["coordinates"] == {"lat": 54.66370, "lng": -5.66544}

    split = common.observation(
        name="Jenny Watts",
        venue="Jenny Watts",
        source="thesession",
        source_url="https://thesession.org/sessions/1",
        place="Bangor",
        address="41 High Street, BT20 5BE",
    )
    assert split["address"] == "41 High Street"
    assert split["post_code"] == "BT20 5BE"
    assert "coordinates" not in split

    uk = common.observation(
        name="Blue Lamp",
        venue="Blue Lamp",
        source="livingtradition",
        source_url="https://example.test/aberdeen",
        place="Aberdeen",
        address="121 Gallowgate, United Kingdom",
    )
    assert uk["address"] == "121 Gallowgate"
    assert "United Kingdom" not in uk["address"]

    cached = common.observation(
        name="Doolin Inn",
        venue="Doolin Inn",
        source="thesession",
        source_url="https://thesession.org/sessions/9",
        place="Doolin",
        coordinates={"lat": 53.01262, "lng": -9.38377},
    )
    assert cached["address"] == "Fisher Street"
    assert cached["post_code"] == "V95 RX23"

    kept = common.observation(
        name="Doolin Inn",
        venue="Doolin Inn",
        source="thesession",
        source_url="https://thesession.org/sessions/9",
        place="Doolin",
        address="Fisherstreet",
        post_code="V95 RX23",
        coordinates={"lat": 53.01262, "lng": -9.38377},
    )
    assert kept["address"] == "Fisherstreet"
    assert kept["post_code"] == "V95 RX23"


def test_future_jsonl_row_cannot_store_a_pin_as_address(monkeypatch, tmp_path):
    monkeypatch.setattr(va, "CACHE_PATH", tmp_path / "empty.json")
    monkeypatch.setattr(va, "_CACHE", None)
    row = {
        "name": "Future Club",
        "source": "future-scraper",
        "place": "Belfast",
        "address": "@54.60000,-5.90000",
    }
    va.normalize_observation_row(row)
    assert "address" not in row
    assert row["coordinates"]["lat"] == 54.6
    assert row["coordinates"]["lng"] == -5.9


def test_corpus_keeps_observation_street_and_postcode(monkeypatch, tmp_path):
    import build_corpus as bc

    monkeypatch.setattr(va, "CACHE_PATH", tmp_path / "empty.json")
    monkeypatch.setattr(va, "_CACHE", None)
    ent = bc.entity_from_cluster(
        [
            {
                "name": "Bill Chawke's Bar",
                "venue": "Bill Chawke's Bar",
                "place": "Adare",
                "county_or_region": "Limerick",
                "address": "Rathkeale Road",
                "post_code": "V94 CX37",
                "source": "thesession",
                "source_url": "https://thesession.org/sessions/1",
                "website": "https://billchawke.com",
                "coordinates": {"lat": 52.56187, "lng": -8.79299},
            }
        ],
        legacy=None,
        new_id=99001,
    )
    assert ent["address"] == "Rathkeale Road"
    assert ent["post_code"] == "V94 CX37"
    assert ent["coordinates"]["lat"] == 52.56187


def test_split_house_road():
    assert va.split_house_road("121 Gallowgate") == ("121", "Gallowgate", [])
    assert va.split_house_road("6 Parkgate, Huddersfield") == (
        "6",
        "Parkgate",
        ["Huddersfield"],
    )
    assert va.split_house_road("West Street, Alford") == ("", "West Street", ["Alford"])
    assert va.split_house_road("16-18 St Mary's Street") == (
        "16-18",
        "St Mary's Street",
        [],
    )
    assert va.looks_like_street("121 Gallowgate")
    assert va.looks_like_street("Meadow Road, Catshill")
    assert not va.looks_like_street("Wallingford")
    assert not va.looks_like_street("North Somerset")


def test_pick_street_postcode_rejects_school_and_conflicting_town():
    school = [
        {
            "category": "amenity",
            "type": "school",
            "addresstype": "amenity",
            "name": "Brindle Gregson Lane Primary School",
            "display_name": "Brindle Gregson Lane Primary School, Gregson Lane, Preston, PR5 0DR",
            "address": {
                "amenity": "Brindle Gregson Lane Primary School",
                "road": "Gregson Lane",
                "town": "Preston",
                "postcode": "PR5 0DR",
            },
        }
    ]
    assert va.pick_street_postcode(
        "Gregson Lane", "Preston", school, venue="Nets Bar"
    ) is None

    manchester = [
        {
            "category": "shop",
            "type": "hairdresser",
            "addresstype": "building",
            "name": "AcuSpa",
            "display_name": "AcuSpa, 50 Bridge Street, Manchester, M3 3BW",
            "address": {
                "house_number": "50",
                "road": "Bridge Street",
                "city": "Manchester",
                "postcode": "M3 3BW",
            },
        }
    ]
    assert va.pick_street_postcode(
        "50 Bridge Street, Manchester",
        "Tintagel",
        manchester,
        venue="The Gas Lamp",
    ) is None


def test_pick_street_postcode_matches_house_and_rejects_city():
    results = [
        {
            "lat": "57.15000",
            "lon": "-2.10000",
            "category": "place",
            "type": "city",
            "addresstype": "city",
            "name": "Aberdeen",
            "display_name": "Aberdeen, AB10 1AA, United Kingdom",
            "address": {"city": "Aberdeen", "postcode": "AB10 1AA"},
        },
        {
            "lat": "57.15100",
            "lon": "-2.09800",
            "category": "amenity",
            "type": "pub",
            "addresstype": "amenity",
            "name": "The Blue Lamp",
            "display_name": "The Blue Lamp, 121, Gallowgate, Aberdeen, AB25 1BU, United Kingdom",
            "address": {
                "amenity": "The Blue Lamp",
                "house_number": "121",
                "road": "Gallowgate",
                "city": "Aberdeen",
                "postcode": "AB25 1BU",
            },
        },
    ]
    hit = va.pick_street_postcode("121 Gallowgate", "Aberdeen", results, venue="Blue Lamp")
    assert hit is not None
    assert hit["post_code"] == "AB25 1BU"
    assert hit["address"] == "121 Gallowgate"


def test_pick_street_postcode_rejects_other_town_high_street():
    results = [
        {
            "lat": "53.96000",
            "lon": "-1.08000",
            "category": "highway",
            "type": "residential",
            "addresstype": "road",
            "name": "High Street",
            "display_name": "High Street, York, YO1 8QH, United Kingdom",
            "address": {"road": "High Street", "city": "York", "postcode": "YO1 8QH"},
        }
    ]
    assert va.pick_street_postcode("High Street", "Bath", results) is None


def test_is_fill_target_street_without_pin():
    import fill_venue_addresses as fill

    assert fill.is_fill_target(
        {
            "venue": "Blue Lamp",
            "address": "121 Gallowgate",
            "place": "Aberdeen",
            "post_code": "",
        }
    )
    assert not fill.is_fill_target(
        {
            "venue": "Blue Lamp",
            "address": "121 Gallowgate",
            "place": "Aberdeen",
            "post_code": "AB25 1BU",
        }
    )
    assert not fill.is_fill_target(
        {"venue": "Blue Lamp", "address": "", "place": "Aberdeen", "post_code": ""}
    )
    assert fill.is_fill_target(
        {
            "venue": "Blue Lamp",
            "address": "",
            "place": "Aberdeen",
            "post_code": "",
            "lat": 57.15,
            "lng": -2.10,
        }
    )
