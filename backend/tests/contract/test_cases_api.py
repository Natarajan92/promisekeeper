"""Saved-state discovery, raw evidence, and strict selected-copy ownership."""

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from test_common_api import HEADERS, app_for, payload


def new_demo(client, variant=None, clock="REFERENCE"):
    request = payload() | {"variant_id": variant, "clock_mode": clock}
    response = client.post("/api/v1/demonstrations", json=request, headers=HEADERS)
    assert response.status_code == 201, response.text
    did = response.json()["demonstration_id"]
    response = client.get(f"/api/v1/demonstrations/{did}/cases")
    assert response.status_code == 200, response.text
    return did, response.json()["cases"]


def test_discovery_is_read_only_three_cases_and_exact_raw_sources_survive_restart(tmp_path):
    path = tmp_path / "cases.sqlite"
    with TestClient(app_for(path), base_url="http://127.0.0.1:8000") as client:
        assert client.get("/api/v1/demonstrations").json() == {"schema_version": "1", "demonstrations": []}
        did, cases = new_demo(client)
        assert [c["catalogue_case_id"] for c in cases] == ["PK-001", "PK-002", "PK-003"]
        assert cases[0]['due_text']=='10 October 2026'
        assert cases[0]['due_at']=='2026-10-10T18:30:00+00:00'
        view = client.get(f"/api/v1/cases/{cases[0]['id']}", params={"demonstration_id": did}).json()
        assert view["financial_facts"]["balance"]["minor_units"] == "8000000"
        assert view["latest_completed_result"] is None
        assert view["current_result"] is None
        assert view["current_draft_version_id"] is None
        assert view["review_epoch"] == 0
        assert view["allowed_commands"]["start_investigation"]["allowed"] is True
        invoice = next(e for e in view["evidence"] if e["kind"] == "INVOICE")
        assert invoice["original_content"] == "Fictional invoice NS-104; client Northstar Analytics; INR 120,000.00; due 10 October 2026."
        assert invoice["event_at"] is None
        source = client.get(f"/api/v1/evidence-versions/{invoice['id']}", params={"demonstration_id": did})
        assert source.json() == invoice
        assert "candidate" not in source.text
        second, _ = new_demo(client)
        summaries = client.get("/api/v1/demonstrations").json()["demonstrations"]
        assert [s["id"] for s in summaries] == [did, second]
        assert summaries[0]["selected_variant_id"] is None
        assert all(datetime.fromisoformat(s["created_at"]).utcoffset().total_seconds() == 0 for s in summaries)
    with TestClient(app_for(path), base_url="http://127.0.0.1:8000") as client:
        assert client.get("/api/v1/demonstrations").json()["demonstrations"] == summaries
        assert client.get(f"/api/v1/cases/{cases[0]['id']}", params={"demonstration_id": did}).json() == view


def test_copy_ownership_and_unknown_payment_never_becomes_zero(tmp_path):
    with TestClient(app_for(tmp_path / "cases.sqlite"), base_url="http://127.0.0.1:8000") as client:
        a, cases = new_demo(client, "FV-05")
        b, _ = new_demo(client)
        cid = next(c["id"] for c in cases if c["catalogue_case_id"] == "PK-003")
        assert client.get(f"/api/v1/cases/{cid}", params={"demonstration_id": b}).status_code == 404
        view = client.get(f"/api/v1/cases/{cid}", params={"demonstration_id": a}).json()
        assert view["ledger_availability"] == "UNAVAILABLE"
        assert view["financial_facts"]["balance"] is None
        assert view["financial_facts"]["paid"] is None
        sid = view["evidence"][0]["id"]
        assert client.get(f"/api/v1/evidence-versions/{sid}", params={"demonstration_id": b}).status_code == 404
        assert client.get(f"/api/v1/cases/{cid}").status_code == 422


@pytest.mark.parametrize("changes", [{"variant_id": "unregistered"}, {"catalogue_version": "made-up"},
    {"clock_mode": "OTHER"}, {"schema_version": 1}, {"operation_id": 123}, {"evidence": []},
    {"variant_id": False}, {"clock_mode": 1}])
def test_unapproved_and_coerced_creation_fields_are_rejected(tmp_path, changes):
    with TestClient(app_for(tmp_path / "cases.sqlite"), base_url="http://127.0.0.1:8000") as client:
        response = client.post("/api/v1/demonstrations", json=payload() | changes, headers=HEADERS)
        assert response.status_code == 422
        assert client.get("/api/v1/demonstrations").json()["demonstrations"] == []


def test_all_registered_variants_persist_with_foreign_keys_and_distinct_anchors(tmp_path):
    from promisekeeper.fixtures.catalogue import variant_ids
    app = app_for(tmp_path / "cases.sqlite")
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        for variant in variant_ids():
            did, cases = new_demo(client, variant)
            for row in cases:
                response = client.get(f"/api/v1/cases/{row['id']}", params={"demonstration_id": did})
                assert response.status_code == 200, (variant, response.text)
        with app.state.db.connection() as con:
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []
            assert con.execute("SELECT count(*) FROM commitment_attributions").fetchone()[0] > 0


def test_real_clock_is_server_derived_and_not_user_supplied(tmp_path):
    with TestClient(app_for(tmp_path / "cases.sqlite"), base_url="http://127.0.0.1:8000") as client:
        did, cases = new_demo(client, clock="REAL")
        view = client.get(f"/api/v1/cases/{cases[0]['id']}", params={"demonstration_id": did}).json()
        assert view["clock_mode"] == "REAL"
        assert datetime.fromisoformat(view["evaluation_at"]).year >= 2026


def test_deletion_is_selected_confirmed_replayable_and_content_free(tmp_path):
    with TestClient(app_for(tmp_path / "cases.sqlite"), base_url="http://127.0.0.1:8000") as client:
        did, cases = new_demo(client, "FV-16-LINKED")
        other, _ = new_demo(client)
        body = dict(schema_version="1", operation_id=str(uuid4()), confirmed_demonstration_id=did, confirm=True)
        for change in ({"confirmed_demonstration_id": other}, {"confirm": False}, {"confirm": 1}):
            assert client.post(f"/api/v1/demonstrations/{did}/deletion", json=body | change, headers=HEADERS).status_code == 422
        saved = client.post(f"/api/v1/demonstrations/{did}/deletion", json=body, headers=HEADERS)
        assert saved.status_code == 200, saved.text
        assert client.post(f"/api/v1/demonstrations/{did}/deletion", json=body, headers=HEADERS).json() == saved.json()
        assert client.get(f"/api/v1/cases/{cases[0]['id']}", params={"demonstration_id": did}).status_code == 404
        assert [d["id"] for d in client.get("/api/v1/demonstrations").json()["demonstrations"]] == [other]


def test_latest_completed_freshness_and_paginated_immutable_history(tmp_path):
    from promisekeeper.application.start_investigation import start_investigation
    from support.workflow_records import seed_completed
    from test_scenario_events_api import confirmation, preview_for
    app = app_for(tmp_path / "cases.sqlite")
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        did, cases = new_demo(client)
        cid = cases[1]["id"]
        start = start_investigation(app.state.db, did, cid, dict(schema_version="1", operation_id=str(uuid4()), expected_case_revision=0, retry_of=None))
        result = seed_completed(app.state.db, start, action="WAIT", review_at="2026-10-25T18:30:00+00:00")
        view = client.get(f"/api/v1/cases/{cid}", params={"demonstration_id": did}).json()
        assert view["current_result"] == result
        p = preview_for(client, did, cid, "PK-002-U1")
        assert client.post(f"/api/v1/cases/{cid}/scenario-events", params={"demonstration_id": did}, json=confirmation(p), headers=HEADERS).status_code == 200
        view = client.get(f"/api/v1/cases/{cid}", params={"demonstration_id": did}).json()
        assert view["freshness"] == "TIME_EXPIRED"
        assert view["current_result"] is None
        assert view["latest_completed_result"] == result
        assert view["review_required"] is True
        sequences, cursor = [], 0
        while True:
            page = client.get(f"/api/v1/cases/{cid}/history", params={"demonstration_id": did, "limit": 1, "cursor": cursor}).json()
            sequences.extend(e["sequence"] for e in page["events"])
            cursor = page["next_cursor"]
            if cursor is None:
                break
        assert sequences == list(range(1, 7))
        assert client.get(f"/api/v1/cases/{cid}/history", params={"demonstration_id": did, "limit": 101}).status_code == 422
