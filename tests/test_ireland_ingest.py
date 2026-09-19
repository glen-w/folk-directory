"""Ireland ingest: counties.yaml, geo scope, publish rules."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingest"))
sys.path.insert(0, str(ROOT / "scripts"))

from ireland_geo import is_island_county, is_roi_county, roi_counties  # noqa: E402
import build_corpus as bc  # noqa: E402
import geocode_listings as g  # noqa: E402
import publish_corpus as pub  # noqa: E402
from postcode import normalize_eircode, normalize_listing_location  # noqa: E402


ROI_EXPECTED = (
    "Carlow",
    "Cavan",
    "Clare",
    "Cork",
    "Donegal",
    "Dublin",
    "Galway",
    "Kerry",
    "Kildare",
    "Kilkenny",
    "Laois",
    "Leitrim",
    "Limerick",
    "Longford",
    "Louth",
    "Mayo",
    "Meath",
    "Monaghan",
    "Offaly",
    "Roscommon",
    "Sligo",
    "Tipperary",
    "Waterford",
    "Westmeath",
    "Wexford",
    "Wicklow",
)


def test_canonical_roi_counties():
    names = roi_counties()
    assert names == ROI_EXPECTED
    assert len(names) == 26
    assert is_roi_county("Dublin")
    assert is_roi_county("Co. Cork")
    assert is_roi_county("queen's county")
    assert not is_roi_county("Antrim")
    assert is_island_county("Antrim")
    assert is_island_county("Galway")


def test_dublin_not_dropped():
    assert not bc.is_out_of_scope(
        {"name": "The Cobblestone", "place": "Dublin", "county_or_region": "Dublin"}
    )
    assert not bc.is_out_of_scope(
        {"name": "Doolin Session", "place": "Doolin", "county": "Clare"}
    )
    assert bc.is_out_of_scope(
        {"name": "Toronto Folk Club", "place": "Toronto", "county": "Ontario"}
    )


def test_ireland_thesession_www_publishable():
    ent = bc.entity_from_cluster(
        [
            {
                "name": "The Cobblestone",
                "event_kind": "session",
                "place": "Dublin",
                "county_or_region": "Dublin",
                "website": "https://cobblestonepub.ie",
                "source": "thesession",
                "source_url": "https://thesession.org/sessions/1",
                "raw_excerpt": "Dublin | Ireland",
            }
        ],
        legacy=None,
        new_id=90001,
    )
    assert ent["publishable"] is True
    assert ent["publish_reason"] == "ireland_thesession_www"
    assert "ireland" in [x.lower() for x in ent["locations"]]


def test_excerpt_mention_does_not_make_uk_ireland():
    """Festivals that mention Ireland in copy must stay GB."""
    assert not bc.island_of_ireland(
        {
            "name": "Cullerlie Traditional Singing Weekend",
            "place": "Cullerlie",
            "county": "Aberdeenshire",
            "locations": ["cullerlie", "aberdeenshire"],
            "raw_excerpt": (
                "singers from Scotland, England, and Ireland. "
                "The event is especially for those who like traditional singing."
            ),
        }
    )
    locs = bc.ensure_ireland_location(
        ["cullerlie", "aberdeenshire", "ireland"],
        "Aberdeenshire",
        {"place": "Cullerlie", "name": "Cullerlie Traditional Singing Weekend"},
    )
    assert "ireland" not in [x.lower() for x in locs]


def test_stale_ireland_slug_stripped_for_gb_county():
    locs = bc.ensure_ireland_location(
        ["ashford", "the-south-west", "ireland"],
        "Devon",
        {"place": "South Molton", "name": "George Hotel"},
    )
    assert "ireland" not in [x.lower() for x in locs]


def test_derry_alias_is_island():
    assert is_island_county("Derry")
    assert bc.island_of_ireland({"county": "Derry", "place": "Derry", "locations": []})


def test_george_hotel_kent_not_merged_with_devon():
    clusters = bc.cluster_observations(
        [
            {
                "name": "George Hotel",
                "website": "http://www.georgehotelsouthmolton.co.uk/",
                "county_or_region": "The South West",
                "place": "",
                "source": "traditionalmusic",
                "raw_excerpt": "The George Hotel , south Molton, Devon Regular concerts.",
            },
            {
                "name": "George Hotel",
                "website": "",
                "county_or_region": "Kent",
                "place": "Ashford",
                "source": "thesession",
                "raw_excerpt": "Ashford | Kent | England",
            },
        ]
    )
    assert len(clusters) == 2


def test_publish_identity_rejects_id_collision():
    assert pub.same_listing_identity(
        {"name": "George Hotel", "title": "George Hotel"},
        {"name": "George Hotel", "title": "George Hotel"},
    )
    assert not pub.same_listing_identity(
        {"name": "George Hotel", "title": "George Hotel"},
        {"name": "Blake's", "title": "Blake's"},
    )


def test_publish_soft_dup_avoids_id_suffix_for_empty_venue():
    """Festivals with empty venue + same place must merge, not create *-NNNN.md."""
    assert pub.same_listing_soft(
        {"title": "Beggars Fair", "place": "Romsey", "county": "Hampshire", "venue": ""},
        {"title": "Beggars Fair", "place": "Romsey", "county": "Hampshire", "venue": ""},
    )
    assert not pub.same_listing_soft(
        {
            "title": "Friel's Bar",
            "place": "Miltown Malbay",
            "county": "Clare",
            "venue": "Friel's Bar",
        },
        {
            "title": "Friel's Bar",
            "place": "Swatragh",
            "county": "Derry",
            "venue": "Friel's Bar",
        },
    )


def test_uk_thesession_still_weak():
    ent = bc.entity_from_cluster(
        [
            {
                "name": "A Random Session",
                "event_kind": "session",
                "place": "Leeds",
                "county_or_region": "West Yorkshire",
                "website": "https://example.com",
                "source": "thesession",
                "source_url": "https://thesession.org/sessions/2",
                "raw_excerpt": "Leeds | England",
            }
        ],
        legacy=None,
        new_id=90002,
    )
    assert ent["publishable"] is False
    assert ent["publish_reason"].startswith("weak_single:")
    assert "ireland" not in [x.lower() for x in ent["locations"]]

def test_pubhub_host_does_not_collapse_venues():
    clusters = bc.cluster_observations(
        [
            {
                "name": "The Cobblestone",
                "website": "https://pubhub.ie/pub/the-cobblestone/",
                "source": "seshie",
                "county_or_region": "Dublin",
            },
            {
                "name": "Tigh Coili",
                "website": "https://pubhub.ie/pub/tigh-coili/",
                "source": "seshie",
                "county_or_region": "Galway",
            },
        ]
    )
    assert len(clusters) == 2


def test_seshie_is_strong():
    ent = bc.entity_from_cluster(
        [
            {
                "name": "Tigh Coili",
                "event_kind": "session",
                "place": "Galway",
                "county_or_region": "Galway",
                "website": "pubhub.ie/pub/tigh-coili",
                "source": "seshie",
                "source_url": "https://sesh.ie/county/galway.html",
                "raw_excerpt": "Sunday trad in Galway",
            }
        ],
        legacy=None,
        new_id=90003,
    )
    assert ent["publishable"] is True
    assert "seshie" in ent["publish_reason"]


def test_geocode_ireland_country_hint():
    addr = g.build_address(
        {"venue": "The Cobblestone", "place": "Smithfield", "county": "Dublin", "address": ""}
    )
    assert addr.endswith("Ireland")
    assert "United Kingdom" not in addr


def test_eircode_normalize():
    addr, place, pc = normalize_listing_location("Smithfield, D07 YX00", "Dublin", "")
    assert pc == "D07 YX00"
    assert "D07" not in addr
    assert normalize_eircode("d07yx00") == "D07 YX00"


def test_thesession_coords_become_entity_and_lat_lng(monkeypatch, tmp_path):
    import venue_address as va

    # Street fill is cache-backed. This test only checks that a pin is not
    # written into `address` when nothing has been looked up yet.
    monkeypatch.setattr(va, "CACHE_PATH", tmp_path / "empty-address-cache.json")
    monkeypatch.setattr(va, "_CACHE", None)
    ent = bc.entity_from_cluster(
        [
            {
                "name": "Jenny Watts",
                "event_kind": "session",
                "place": "Bangor",
                "county_or_region": "Down",
                "website": "https://www.jennywattsbangor.com",
                "source": "thesession",
                "source_url": "https://thesession.org/sessions/3203",
                "raw_excerpt": "Bangor | Down | Northern Ireland | tel 028 9127 0401",
                "coordinates": {"lat": 54.66370, "lng": -5.66544},
            }
        ],
        legacy=None,
        new_id=903203,
    )
    assert ent["coordinates"] == {"lat": 54.66370, "lng": -5.66544}
    fm = pub.public_fm(ent)
    assert fm["address"] == ""
    assert fm["lat"] == 54.66370
    assert fm["lng"] == -5.66544
    assert pub.body_for_new({**ent, "raw_excerpt": "Bangor | Down | Northern Ireland | tel 028 | @54.66370,-5.66544"}) == ""


def test_body_for_new_does_not_fabricate_identity_stub():
    entity = {
        "name": "The Roost",
        "venue": "The Roost",
        "place": "Maynooth",
        "event_types": ["session"],
        "when": "Friday, Every Week",
        "raw_excerpt": "Index: stub",
    }
    assert pub.body_for_new(entity) == ""
    entity["raw_excerpt"] = "The Roost at The Roost (Maynooth) — Friday, Every Week"
    assert pub.body_for_new(entity) == ""
    entity["raw_excerpt"] = "Nice atmosphere."
    assert "atmosphere" in pub.body_for_new(entity).lower()


def test_listicle_name_not_publishable():
    ent = bc.entity_from_cluster(
        [
            {
                "name": "33 Best Pubs in Ireland (2026 Edition)",
                "event_kind": "session",
                "place": "Roundwood",
                "county_or_region": "Antrim",
                "website": "https://www.theirishroadtrip.com/best-things-to-do-in-antrim",
                "source": "searxng",
                "raw_excerpt": "19 Best Things to do in Antrim",
            },
            {
                "name": "33 Best Pubs in Ireland (2026 Edition)",
                "event_kind": "session",
                "place": "Roundwood",
                "county_or_region": "Antrim",
                "website": "https://www.theirishroadtrip.com/best-things-to-do-in-antrim",
                "source": "grok-discovery",
                "raw_excerpt": "tourism listicle",
            },
        ],
        legacy=None,
        new_id=91001,
    )
    assert ent["publishable"] is False
    assert ent["publish_reason"] == "junk_name"


def test_legacy_listing_number_name_replaced_with_venue():
    ent = bc.entity_from_cluster(
        [
            {
                "name": "Listing 411",
                "event_kind": "session",
                "venue": "The Bugle",
                "place": "Botley",
                "county_or_region": "Hampshire",
                "source": "livingtradition",
                "raw_excerpt": "",
            }
        ],
        legacy={
            "id": 411,
            "name": "Listing 411",
            "title": "Listing 411",
            "venue": "The Bugle",
            "place": "Botley",
            "county": "Hampshire",
            "event_types": ["session"],
        },
        new_id=411,
    )
    assert ent["name"] == "Session at The Bugle"
    assert ent["title"] == "Session at The Bugle"
    fm = pub.public_fm(ent)
    assert fm["name"] == "Session at The Bugle"
    assert fm["title"] == "Session at The Bugle"
    assert pub.same_listing_identity(
        {"name": "Listing 411", "venue": "The Bugle"},
        ent,
    )


def test_grok_searxng_pair_not_multi_source():
    ent = bc.entity_from_cluster(
        [
            {
                "name": "Some Dublin Pub",
                "event_kind": "session",
                "place": "Dublin",
                "county_or_region": "Dublin",
                "website": "",
                "source": "searxng",
                "raw_excerpt": "session",
            },
            {
                "name": "Some Dublin Pub",
                "event_kind": "session",
                "place": "Dublin",
                "county_or_region": "Dublin",
                "website": "",
                "source": "grok-discovery",
                "raw_excerpt": "session",
            },
        ],
        legacy=None,
        new_id=91002,
    )
    assert ent["publishable"] is False
    assert ent["publish_reason"] == "weak_discovery_pair"
