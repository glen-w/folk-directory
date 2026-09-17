"""Links hubs / other directories must not publish as event listings."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingest"))
sys.path.insert(0, str(ROOT / "scripts"))

import build_corpus as bc  # noqa: E402
import publish_corpus as pub  # noqa: E402
from links_hubs import host_is_links_hub, links_hub_reason  # noqa: E402


def test_sadfolk_host_is_hub():
    assert host_is_links_hub("www.sadfolk.co.uk")
    assert host_is_links_hub("https://sadfolk.co.uk/events")
    assert links_hub_reason(www="www.sadfolk.co.uk") == "links_hub_host"


def test_normal_venue_host_not_hub():
    assert not host_is_links_hub("https://cobblestonepub.ie")
    assert links_hub_reason(
        name="The Cobblestone",
        www="https://cobblestonepub.ie",
        venue="The Cobblestone",
        when="Monday, 21:00",
    ) is None


def test_guide_copy_without_venue_blocked():
    assert (
        links_hub_reason(
            name="Somewhere Folk",
            www="",
            venue="",
            when="",
            excerpt="Online (and email list) guide to whats happening on the folk scene in Dorset",
        )
        == "links_hub_guide"
    )


def test_harberton_hybrid_not_blocked_by_guide_heuristic():
    """Area guide that also runs concerts — keep until manually reviewed."""
    assert (
        links_hub_reason(
            name="Harberton Folk",
            www="www.harbertonfolk.co.uk",
            venue="",
            when="",
            excerpt="Harberton Folk provides a guide to what's on in the South Devon area, "
            "and organises regular concerts at the Ariel Arts Centre in Totnes.",
        )
        is None
    )


def test_entity_from_cluster_blocks_directory_www():
    ent = bc.entity_from_cluster(
        [
            {
                "name": "Sad Folk",
                "event_kind": "club",
                "place": "",
                "county_or_region": "Somerset",
                "website": "https://www.sadfolk.co.uk/",
                "source": "searxng",
                "source_url": "https://example.com/search",
                "raw_excerpt": "Somerset and Dorset Folk Diary",
            },
            {
                "name": "Sad Folk",
                "event_kind": "club",
                "place": "",
                "county_or_region": "Somerset",
                "website": "https://www.sadfolk.co.uk/",
                "source": "englishfolkinfo",
                "source_url": "https://englishfolkinfo.org.uk/",
                "raw_excerpt": "folk diary",
            },
        ],
        legacy=None,
        new_id=99001,
    )
    assert ent["publishable"] is False
    assert ent["publish_reason"] == "links_hub_host"


def test_legacy_hub_id_blocked():
    ent = bc.entity_from_cluster(
        [
            {
                "name": "Kent Folk",
                "event_kind": "club",
                "website": "https://example-not-in-hub-list.test",
                "source": "livingtradition",
                "source_url": "https://livingtradition.co.uk/",
                "raw_excerpt": "Kent",
            }
        ],
        legacy={"id": 1172, "name": "Kent Folk", "www": "https://example-not-in-hub-list.test"},
        new_id=None,
    )
    assert ent["publishable"] is False
    assert ent["publish_reason"] == "links_hub_id"


def test_publish_module_imports_shared_hub_check():
    assert pub.links_hub_reason(www="norfolkfolk.co.uk") == "links_hub_host"


def test_ireland_tourism_hosts_are_hubs():
    assert host_is_links_hub("www.visitdublin.com")
    assert host_is_links_hub("https://www.theirishroadtrip.com/best-pubs")
    assert host_is_links_hub("www.discoverireland.ie/kerry/folk-in-fusion-yras-live")
    assert host_is_links_hub("www.purecork.ie/whats-on/11191156/smithwicks-sessions-trad-folk")
    assert links_hub_reason(www="www.visitdublin.com") == "links_hub_host"
