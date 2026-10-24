"""Produce the Gate I pure-domain evidence report; no runtime/API/provider execution."""
from importlib.metadata import version
from pathlib import Path
import json
import platform
import sqlite3

from promisekeeper.domain.money import minor_text
from promisekeeper.domain.recommendations import recommend
from promisekeeper.fixtures.catalogue import apply_event, fresh_copy, variant_definition, variant_ids


def collect():
    records = []

    def record(label, demo, cid):
        fixture = demo.cases[cid]
        result = recommend(fixture.evidence, fixture.extraction, demo.evaluation_at)
        expected = dict(fixture.expected)
        balance = result.financial.balance_minor
        actual = dict(action=result.action, balance_minor=minor_text(balance) if balance is not None else None,
                      review_at=result.review_at.isoformat() if result.review_at else None)
        # Compare instants through datetimes; source timezone formatting is preserved separately.
        from datetime import datetime
        review_ok = ((datetime.fromisoformat(actual["review_at"]) if actual["review_at"] else None)
                     == (datetime.fromisoformat(expected["review_at"]) if expected["review_at"] else None))
        passed = actual["action"] == expected["action"] and actual["balance_minor"] == expected["balance_minor"] and review_ok
        records.append(dict(scenario=label, case=cid, expected=expected, actual=actual, passed=passed,
                            status=result.status, reason=result.reason_code, source_refs=result.source_refs))

    baseline = fresh_copy()
    for cid in baseline.cases:
        record("BASELINE", baseline, cid)
        updated = apply_event(fresh_copy(), cid+"-U1")
        record(cid+"-U1", updated, cid)
    workflows = []
    for vid in variant_ids():
        definition = variant_definition(vid)
        if "workflow" in definition:
            workflows.append(dict(variant=vid, workflow_execution="UNEXECUTED"))
            if vid not in {"FV-12", "FV-13"}:
                continue
        demo = fresh_copy(vid)
        record(vid, demo, definition["case_id"])
        if vid in {"FV-18-A", "FV-18-B"}:
            for number in (1,2):
                event = vid+f"-CLOCK-{number}"
                demo = apply_event(demo, event)
                record(event, demo, "PK-002")
    assert all(item["passed"] for item in records), "Domain outcome mismatch; do not publish a passing phase report"
    return dict(scope="Gate I pure domain; no database, API, browser workflow or LLM calls", records=records,
                passed=len(records), total=len(records), workflow_presets=workflows,
                environment=dict(python=platform.python_version(), sqlite=sqlite3.sqlite_version,
                                 packages={name:version(name) for name in ("fastapi","pydantic","openai","pytest","tzdata")}))


if __name__ == "__main__":
    report = collect()
    target = Path(__file__).resolve().parents[3]/"reports/phase-i-fixtures.json"
    target.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(f"Gate I domain outcomes: {report['passed']}/{report['total']}; workflow execution remains unexecuted.")
