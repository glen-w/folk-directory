"""Offline provider-comparison tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compare_geocode_providers as compare  # noqa: E402


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_distance_buckets() -> None:
    assert compare.distance_bucket(0.249) == "agree"
    assert compare.distance_bucket(0.25) == "minor_drift"
    assert compare.distance_bucket(1.999) == "minor_drift"
    assert compare.distance_bucket(2.0) == "investigate"
    assert compare.distance_bucket(12.0) == "investigate"
    assert compare.distance_bucket(12.001) == "strong_disagreement"


def test_compare_uses_cached_data_and_flags_area_centroid(tmp_path: Path) -> None:
    listings = tmp_path / "listings"
    listings.mkdir()
    (listings / "example.md").write_text(
        """---
id: 123
title: Example Folk Club
venue: Example Hall
place: Canterbury
county: Kent
post_code: CT1 1AA
---
""",
        encoding="utf-8",
    )
    map_path = tmp_path / "map.json"
    nom_path = tmp_path / "nominatim.json"
    open_path = tmp_path / "opencage.json"
    postcode_path = tmp_path / "postcodes.json"
    place_path = tmp_path / "places.json"
    query = "Example Hall, Canterbury, CT1 1AA, Kent, United Kingdom"
    write_json(
        map_path,
        {
            "locations": [
                {
                    "permalink": "/listings/example/",
                    "coordinates": {"lat": 51.28, "lng": 1.08},
                }
            ]
        },
    )
    write_json(
        nom_path,
        {
            "locations": {
                query.lower(): {
                    "geocoded": True,
                    "coordinates": {"lat": 51.28, "lng": 1.08},
                }
            }
        },
    )
    write_json(
        open_path,
        {
            "listings": {
                "example": {
                    "status": "ok",
                    "primary_query": query,
                    "coordinates": {"lat": 51.279, "lng": 1.081},
                    "result_type": "city",
                    "confidence": 5,
                }
            }
        },
    )
    write_json(postcode_path, {"CT1 1AA": {"lat": 51.279, "lng": 1.081}})
    write_json(
        place_path,
        {
            "canterbury|kent|united kingdom": {
                "coords": {"lat": 51.28, "lng": 1.08}
            }
        },
    )

    report = compare.compare(
        listings_dir=listings,
        map_path=map_path,
        nominatim_path=nom_path,
        opencage_path=open_path,
        postcode_path=postcode_path,
        place_path=place_path,
    )

    row = report["listings"][0]
    assert row["classification"] == "agree"
    assert row["baseline_source"] == "published"
    assert row["nominatim_source"] == "nominatim"
    assert row["opencage_coarse_result"] is True
    assert "opencage_result_is_area_centroid" in row["flags"]
    assert row["opencage_to_postcode_km"] == 0.0


def test_compare_is_offline_when_opencage_cache_is_absent(tmp_path: Path) -> None:
    listings = tmp_path / "listings"
    listings.mkdir()
    (listings / "missing.md").write_text(
        "---\ntitle: Missing\nplace: York\ncounty: North Yorkshire\n---\n",
        encoding="utf-8",
    )
    map_path = tmp_path / "map.json"
    write_json(
        map_path,
        {
            "locations": [
                {
                    "permalink": "/listings/missing/",
                    "coordinates": {"lat": 53.96, "lng": -1.08},
                }
            ]
        },
    )

    report = compare.compare(
        listings_dir=listings,
        map_path=map_path,
        nominatim_path=tmp_path / "no-nom.json",
        opencage_path=tmp_path / "no-open.json",
        postcode_path=tmp_path / "no-postcode.json",
        place_path=tmp_path / "no-place.json",
    )

    assert report["metadata"]["counts"] == {"existing_only": 1}
    assert report["listings"][0]["opencage_status"] == "not_cached"


def test_explicit_pin_is_measured_but_non_comparable(tmp_path: Path) -> None:
    listings = tmp_path / "listings"
    listings.mkdir()
    (listings / "pinned.md").write_text(
        "---\ntitle: Pinned\nplace: York\ncounty: North Yorkshire\n"
        "lat: 53.9600\nlng: -1.0800\n---\n",
        encoding="utf-8",
    )
    map_path = tmp_path / "map.json"
    open_path = tmp_path / "opencage.json"
    write_json(map_path, {"locations": []})
    write_json(
        open_path,
        {
            "listings": {
                "pinned": {
                    "status": "ok",
                    "primary_query": "Pinned, York, United Kingdom",
                    "coordinates": {"lat": 53.961, "lng": -1.081},
                    "result_type": "building",
                }
            }
        },
    )

    report = compare.compare(
        listings_dir=listings,
        map_path=map_path,
        nominatim_path=tmp_path / "no-nom.json",
        opencage_path=open_path,
        postcode_path=tmp_path / "no-postcode.json",
        place_path=tmp_path / "no-place.json",
    )

    row = report["listings"][0]
    assert row["classification"] == "non_comparable"
    assert row["baseline_source"] == "body-coords"
    assert row["distance_bucket"] == "agree"
    assert row["distance_km"] is not None
