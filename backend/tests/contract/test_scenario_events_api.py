"""Confirmation binds exact catalogue changes to a selected copy, case, and revision."""

import hashlib
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from test_common_api import HEADERS, app_for
from test_cases_api import new_demo


def confirmation(preview):
    return dict(schema_version="1", operation_id=str(uuid4()),
                expected_case_revision=preview["expected_case_revision"], event_id=preview["event_id"],
                catalogue_version=preview["catalogue_version"], confirmed_preview_hash=preview["preview_hash"])


def preview_for(client, did, cid, event):
    response = client.get(f"/api/v1/cases/{cid}/scenario-events/{event}/preview", params={"demonstration_id": did})
    assert response.status_code == 200, response.text
    return response.json()


def test_catalogue_event_eligibility_matches_baseline_and_selected_variant_preview(tmp_path):
    with TestClient(app_for(tmp_path / "eligibility.sqlite"), base_url="http://127.0.0.1:8000") as client:
        events = {event["id"]: event for event in client.get("/api/v1/catalogue").json()["events"]}
        assert events["FV-17-EVIDENCE-RUN-START"]["eligible_variant_ids"] == ["FV-17-EVIDENCE"]
        assert None in events["PK-001-U1"]["eligible_variant_ids"]
        assert "FV-17-EVIDENCE" in events["PK-001-U1"]["eligible_variant_ids"]
        for variant, expected_status in [(None, 422), ("FV-17-EVIDENCE", 200)]:
            did, cases = new_demo(client, variant)
            cid = next(case["id"] for case in cases if case["catalogue_case_id"] == "PK-001")
            response = client.get(f"/api/v1/cases/{cid}/scenario-events/FV-17-EVIDENCE-RUN-START/preview",
                                  params={"demonstration_id": did})
            assert response.status_code == expected_status, response.text


def test_read_only_preview_hash_confirmation_replay_and_foreign_target_rejection(tmp_path):
    app = app_for(tmp_path / "scenarios.sqlite")
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        did, cases = new_demo(client)
        cid = cases[0]["id"]
        params = {"demonstration_id": did}
        before = client.get(f"/api/v1/cases/{cid}", params=params).json()
        preview = preview_for(client, did, cid, "PK-001-U1")
        assert client.get(f"/api/v1/cases/{cid}", params=params).json() == before
        body = {k: v for k, v in preview.items() if k != "preview_hash"}
        encoded = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        assert preview["preview_hash"] == hashlib.sha256(encoded).hexdigest()
        assert preview["evidence_changes"]
        request = confirmation(preview)
        wrong = request | {"confirmed_preview_hash": "0" * 64}
        assert client.post(f"/api/v1/cases/{cid}/scenario-events", params=params, json=wrong, headers=HEADERS).json()["error"]["code"] == "PREVIEW_CHANGED"
        other, others = new_demo(client)
        assert client.post(f"/api/v1/cases/{others[0]['id']}/scenario-events", params={"demonstration_id": other}, json=request, headers=HEADERS).status_code == 409
        assert client.post(f"/api/v1/cases/{cases[1]['id']}/scenario-events", params=params, json=request, headers=HEADERS).status_code == 422
        saved = client.post(f"/api/v1/cases/{cid}/scenario-events", params=params, json=request, headers=HEADERS)
        assert saved.status_code == 200, saved.text
        assert client.post(f"/api/v1/cases/{cid}/scenario-events", params=params, json=request, headers=HEADERS).json() == saved.json()
        after = client.get(f"/api/v1/cases/{cid}", params=params).json()
        assert after["evidence_revision"] == 1
        assert after["case_revision"] == 1
        assert after["review_epoch"] == 1
        assert set(e["id"] for e in before["evidence"]) < set(e["id"] for e in after["evidence"])
        stale = confirmation(preview)
        response = client.post(f"/api/v1/cases/{cid}/scenario-events", params=params, json=stale, headers=HEADERS)
        assert response.json()["error"]["code"] == "REVISION_CONFLICT"
        # Reusing a confirmed operation for changed content conflicts even after revision changes.
        response = client.post(f"/api/v1/cases/{cid}/scenario-events", params=params, json=request | {"event_id": "PK-003-U1"}, headers=HEADERS)
        assert response.json()["error"]["code"] == "OPERATION_PAYLOAD_MISMATCH"


@pytest.mark.parametrize("changes", [{"expected_case_revision": "0"}, {"expected_case_revision": True},
    {"records": []}, {"verification_status": "VERIFIED"}, {"evaluation_at": "2026-10-25T00:00:00Z"},
    {"confirmed_preview_hash": "NOT_A_HASH"}])
def test_no_arbitrary_evidence_time_verification_or_coercion(tmp_path, changes):
    with TestClient(app_for(tmp_path / "scenarios.sqlite"), base_url="http://127.0.0.1:8000") as client:
        did, cases = new_demo(client)
        cid = cases[0]["id"]
        p = preview_for(client, did, cid, "PK-001-U1")
        response = client.post(f"/api/v1/cases/{cid}/scenario-events", params={"demonstration_id": did}, json=confirmation(p) | changes, headers=HEADERS)
        assert response.status_code == 422
        assert client.get(f"/api/v1/cases/{cid}", params={"demonstration_id": did}).json()["case_revision"] == 0


def test_confirmed_clock_event_invalidates_all_case_scopes_and_rejects_backward_clock(tmp_path):
    with TestClient(app_for(tmp_path / "scenarios.sqlite"), base_url="http://127.0.0.1:8000") as client:
        did, cases = new_demo(client, "FV-18-A")
        catalogue = client.get("/api/v1/catalogue").json()
        clocks = [e for e in catalogue["events"] if e["id"].startswith("FV-18-A")]
        assert len(clocks) == 2
        cid = next(c["id"] for c in cases if c["catalogue_case_id"] == clocks[0]["case_id"])
        last = sorted(clocks, key=lambda e: e["evaluation_at"])[-1]
        p = preview_for(client, did, cid, last["id"])
        assert p["clock_change"]["to"].startswith("2026-10-26T18:30:00")
        assert client.post(f"/api/v1/cases/{cid}/scenario-events", params={"demonstration_id": did}, json=confirmation(p), headers=HEADERS).status_code == 200
        earlier = sorted(clocks, key=lambda e: e["evaluation_at"])[0]
        response = client.get(f"/api/v1/cases/{cid}/scenario-events/{earlier['id']}/preview", params={"demonstration_id": did})
        assert response.status_code == 409
        views = [client.get(f"/api/v1/cases/{c['id']}", params={"demonstration_id": did}).json() for c in cases]
        assert all(v["case_revision"] == 1 and v["review_epoch"] == 1 for v in views)
