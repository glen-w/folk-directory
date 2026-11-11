"""Hugo–corpus ID join: identity vs collision, www/name stamp, displace."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import reconcile_hugo_corpus_ids as rec  # noqa: E402


def test_matched_id_when_names_agree():
    hugo = [{"id": 54, "name": "Oxford Folk Club", "title": "Oxford Folk Club", "county": "Oxfordshire"}]
    corpus = [{"id": 54, "name": "Oxford Folk Club", "title": "Oxford Folk Club", "county": "Oxfordshire"}]
    b = rec.join_rows(hugo, corpus)
    assert len(b["matched_id"]) == 1
    assert b["stamp"] == []
    assert b["id_collision"] == []


def test_id_collision_different_names():
    hugo = [{"id": 54, "name": "Oxford Folk Club", "title": "Oxford Folk Club"}]
    corpus = [{"id": 54, "name": "Blake's", "title": "Blake's"}]
    b = rec.join_rows(hugo, corpus)
    assert len(b["id_collision"]) == 1
    assert b["matched_id"] == []


def test_www_stamp_when_ids_differ():
    hugo = [
        {
            "id": 54,
            "name": "Oxford Folk Club",
            "title": "Oxford Folk Club",
            "www": "oxfordfolkclub.com",
            "county": "Oxfordshire",
        }
    ]
    corpus = [
        {
            "id": 13000,
            "name": "Oxford Folk Club",
            "title": "Oxford Folk Club",
            "www": "https://oxfordfolkclub.com/",
            "county": "Oxfordshire",
        }
    ]
    b = rec.join_rows(hugo, corpus)
    assert len(b["stamp"]) == 1
    rec_row = b["stamp"][0]
    assert rec_row["old_id"] == 13000
    assert rec_row["new_id"] == 54
    assert rec_row["via"] == "www"


def test_name_stamp_when_www_missing():
    hugo = [
        {
            "id": 10,
            "name": "Tigerfolk",
            "title": "Tigerfolk",
            "venue": "The Royal Oak",
            "county": "Derbyshire",
        }
    ]
    corpus = [
        {
            "id": 9999,
            "name": "Tigerfolk",
            "title": "Tigerfolk",
            "venue": "The Royal Oak",
            "county": "Derbyshire",
        }
    ]
    b = rec.join_rows(hugo, corpus)
    assert len(b["stamp"]) == 1
    assert b["stamp"][0]["via"] == "name"
    assert b["stamp"][0]["new_id"] == 10


def test_facebook_www_is_not_a_join_key():
    hugo = [
        {
            "id": 1,
            "name": "Club A",
            "title": "Club A",
            "www": "facebook.com/groups/123",
            "county": "Kent",
            "venue": "Hall",
        }
    ]
    corpus = [
        {
            "id": 2,
            "name": "Club B",
            "title": "Club B",
            "www": "facebook.com/groups/123",
            "county": "Kent",
            "venue": "Other",
        }
    ]
    b = rec.join_rows(hugo, corpus)
    assert b["stamp"] == []
    assert any(r["id"] == 1 for r in b["hugo_only"])


def test_ambiguous_www_not_stamped():
    hugo = [
        {
            "id": 1,
            "name": "Worcester Folk Club",
            "title": "Worcester Folk Club",
            "www": "worcesterfolk.org.uk",
            "county": "Worcestershire",
        }
    ]
    corpus = [
        {"id": 10, "name": "Worcester Folk Club", "www": "worcesterfolk.org.uk", "county": "Worcestershire"},
        {"id": 11, "name": "Worcester Folk Festival", "www": "worcesterfolk.org.uk", "county": "Worcestershire"},
    ]
    b = rec.join_rows(hugo, corpus)
    assert b["stamp"] == []
    assert len(b["ambiguous"]) == 1
    assert b["ambiguous"][0]["reason"] == "www"


def test_displace_occupant_then_stamp():
    corpus = [
        {"id": 54, "name": "Wrong occupant"},
        {"id": 13000, "name": "Oxford Folk Club"},
    ]
    stamp = [{"old_id": 13000, "new_id": 54}]
    remap, notes = rec.plan_id_moves(stamp, corpus)
    assert remap[13000] == 54
    assert remap[54] != 54
    assert remap[54] not in {54, 13000}
    actions = {n["action"] for n in notes}
    assert "displace" in actions
    assert "stamp" in actions


def test_apply_remap_rewrites_ids():
    rows = [{"id": 13000, "name": "Oxford"}, {"id": 54, "name": "Other"}]
    n = rec.apply_remap(rows, {13000: 54, 54: 20000})
    assert n == 2
    by_name = {r["name"]: r["id"] for r in rows}
    assert by_name["Oxford"] == 54
    assert by_name["Other"] == 20000
