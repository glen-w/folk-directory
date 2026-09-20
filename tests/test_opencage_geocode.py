"""OpenCage adapter/cache tests; no network calls."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import geocode_opencage_cache as cache_lane  # noqa: E402
from opencage_geocode import OpenCageClient, OpenCageError  # noqa: E402


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = requests.Response()
            response.status_code = self.status_code
            raise requests.HTTPError(f"HTTP {self.status_code}", response=response)

    def json(self) -> dict:
        return self.payload


def test_client_normalizes_top_result_and_rate() -> None:
    response = FakeResponse(
        {
            "status": {"code": 200, "message": "OK"},
            "rate": {"remaining": 2499},
            "results": [
                {
                    "geometry": {"lat": 53.2161, "lng": -6.6661},
                    "formatted": "33 South Main, Naas, Ireland",
                    "components": {"_type": "building", "postcode": "W91"},
                    "confidence": 9,
                }
            ],
        }
    )
    client = OpenCageClient("test-key", min_interval=0, request_get=lambda *_a, **_k: response)

    result = client.geocode("33 South Main, Naas")

    assert result is not None
    assert result["coordinates"] == {"lat": 53.2161, "lng": -6.6661}
    assert result["result_type"] == "building"
    assert client.rate_remaining == 2499


def test_client_handles_zero_results_and_body_error() -> None:
    miss = FakeResponse({"status": {"code": 200}, "total_results": 0, "results": []})
    client = OpenCageClient("test-key", min_interval=0, request_get=lambda *_a, **_k: miss)
    assert client.geocode("NOWHERE-INTERESTING") is None

    failed = FakeResponse({"status": {"code": 402, "message": "quota exceeded"}, "results": []})
    client = OpenCageClient("test-key", min_interval=0, request_get=lambda *_a, **_k: failed)
    with pytest.raises(OpenCageError) as exc:
        client.geocode("Naas")
    assert exc.value.status_code == 402
    assert exc.value.retryable is True


def test_client_tolerates_missing_optional_result_fields() -> None:
    response = FakeResponse(
        {
            "status": {"code": 200},
            "results": [{"geometry": {"lat": 54.0, "lng": -2.0}}],
        }
    )
    client = OpenCageClient("test-key", min_interval=0, request_get=lambda *_a, **_k: response)

    result = client.geocode("Somewhere")

    assert result is not None
    assert result["components"] == {}
    assert result["formatted"] == ""
    assert result["result_type"] == ""
    assert result["confidence"] is None


class CountingClient:
    def __init__(self, result: dict | None = None) -> None:
        self.calls: list[str] = []
        self.result = result

    def geocode(self, query: str) -> dict | None:
        self.calls.append(query)
        return self.result


def test_initial_lane_uses_one_query_and_resumes_from_miss(tmp_path: Path) -> None:
    listing = tmp_path / "example.md"
    listing.write_text(
        """---
title: Example Folk Club
venue: Example Hall
address: 10 High Street
place: Exampletown
county: Kent
post_code: CT1 1AA
---
""",
        encoding="utf-8",
    )
    cache = cache_lane.empty_cache()
    first = CountingClient()

    row, calls = cache_lane.process_listing(
        listing,
        cache=cache,
        client=first,  # type: ignore[arg-type]
        force=False,
        retry_fallbacks=False,
        calls_left=10,
    )

    assert row["status"] == "miss"
    assert calls == 1
    assert len(first.calls) == 1
    assert len(cache["locations"]) == 1

    resumed = CountingClient()
    row, calls = cache_lane.process_listing(
        listing,
        cache=cache,
        client=resumed,  # type: ignore[arg-type]
        force=False,
        retry_fallbacks=False,
        calls_left=10,
    )
    assert row["status"] == "miss"
    assert calls == 0
    assert resumed.calls == []


def test_lane_respects_zero_call_budget(tmp_path: Path) -> None:
    listing = tmp_path / "example.md"
    listing.write_text("---\ntitle: Example\nplace: Canterbury\ncounty: Kent\n---\n", encoding="utf-8")
    client = CountingClient()

    row, calls = cache_lane.process_listing(
        listing,
        cache=cache_lane.empty_cache(),
        client=client,  # type: ignore[arg-type]
        force=False,
        retry_fallbacks=False,
        calls_left=0,
    )

    assert row["status"] == "budget_exhausted"
    assert calls == 0
    assert client.calls == []


def test_cache_schema_round_trip_and_never_contains_api_key(tmp_path: Path) -> None:
    path = tmp_path / "opencage-cache.json"
    cache = cache_lane.empty_cache()
    cache_lane.cache_result(
        cache,
        query="Example Hall, York",
        result={
            "coordinates": {"lat": 53.96, "lng": -1.08},
            "formatted": "Example Hall, York, UK",
            "components": {"_type": "building"},
            "result_type": "building",
            "confidence": 9,
        },
    )

    cache_lane.save_cache(cache, path)
    saved = path.read_text(encoding="utf-8")
    loaded = cache_lane.load_cache(path)

    assert loaded["metadata"]["schema_version"] == cache_lane.SCHEMA_VERSION
    assert loaded["metadata"]["provider"] == "opencage"
    assert "secret-test-key" not in saved
    assert loaded["locations"]["example hall, york"]["geocoded"] is True


class ErrorClient:
    def geocode(self, _query: str) -> None:
        raise OpenCageError("quota exceeded", status_code=402, retryable=True)


def test_quota_error_tells_batch_to_stop(tmp_path: Path) -> None:
    listing = tmp_path / "example.md"
    listing.write_text("---\ntitle: Example\nplace: Canterbury\ncounty: Kent\n---\n", encoding="utf-8")

    row, calls = cache_lane.process_listing(
        listing,
        cache=cache_lane.empty_cache(),
        client=ErrorClient(),  # type: ignore[arg-type]
        force=False,
        retry_fallbacks=False,
        calls_left=10,
    )

    assert calls == 1
    assert row["status"] == "error"
    assert row["error_status"] == 402
    assert row["stop_run"] is True
