"""Contracts for the shared website URL normalizer (cards + map popups)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
UTILS = ROOT / "static" / "js" / "folk-utils.js"
MAP_JS = ROOT / "static" / "js" / "folk-map.js"
BROWSE_JS = ROOT / "static" / "js" / "listings-browse.js"
MAP_JSON = ROOT / "static" / "data" / "listings-map.json"

NODE = shutil.which("node")


def _run_js(expr: str):
    if not NODE:
        pytest.skip("node is not installed")
    script = f"""
const fs = require("fs");
const vm = require("vm");
const sandbox = {{ window: {{}} }};
vm.runInNewContext(fs.readFileSync({json.dumps(str(UTILS))}, "utf8"), sandbox);
const U = sandbox.window.FolkUtils;
const out = {expr};
process.stdout.write(JSON.stringify(out));
"""
    proc = subprocess.run(
        [NODE, "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)


def test_templates_load_folk_utils_before_consumers():
    list_html = (ROOT / "layouts" / "listings" / "list.html").read_text(encoding="utf-8")
    map_html = (ROOT / "layouts" / "_default" / "map.html").read_text(encoding="utf-8")
    home = (ROOT / "layouts" / "index.html").read_text(encoding="utf-8")
    assert list_html.index("/js/folk-utils.js") < list_html.index("/js/listings-browse.js")
    assert map_html.index("/js/folk-utils.js") < map_html.index("/js/folk-map.js")
    assert home.index("/js/folk-utils.js") < home.index("/js/folk-map.js")


def test_consumers_call_shared_normalizer():
    browse = BROWSE_JS.read_text(encoding="utf-8")
    folk_map = MAP_JS.read_text(encoding="utf-8")
    assert "FolkUtils.normalizeWebsiteUrl" in browse
    assert "FolkUtils.displayDomain" in browse
    assert "FolkUtils.normalizeWebsiteUrl(loc.www)" in folk_map
    assert "FolkUtils.displayDomain" in folk_map


def test_map_json_carries_www():
    data = json.loads(MAP_JSON.read_text(encoding="utf-8"))
    locations = data["locations"]
    assert locations
    assert "www" in locations[0]
    with_www = [loc for loc in locations if str(loc.get("www") or "").strip()]
    assert len(with_www) >= 700


def test_normalize_website_url_cases():
    cases = _run_js(
        """[
          U.normalizeWebsiteUrl(""),
          U.normalizeWebsiteUrl("  "),
          U.normalizeWebsiteUrl("info@example.test"),
          U.normalizeWebsiteUrl("not a url"),
          U.normalizeWebsiteUrl("example.test/gigs"),
          U.normalizeWebsiteUrl("//example.test"),
          U.normalizeWebsiteUrl("https://Example.test/path"),
          U.normalizeWebsiteUrl("http://example.test"),
          U.displayDomain("https://www.Example.test/gigs"),
          U.displayDomain("https://example.test")
        ]"""
    )
    assert cases == [
        "",
        "",
        "",
        "",
        "https://example.test/gigs",
        "https://example.test",
        "https://Example.test/path",
        "http://example.test",
        "Example.test",
        "example.test",
    ]
