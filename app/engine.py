from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any
from .db import transaction

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _json_ids(values: list[str]) -> str:
    return json.dumps(sorted(set(values)))

def investigate(today: date | None = None) -> dict[str, int]:
    """Recompute deterministic, explainable findings from stored records."""
    today = today or date.today()
    stamp = now_iso()
    created = 0
    updated = 0
    with transaction() as conn:
        commitments = conn.execute("SELECT * FROM commitments").fetchall()
        for c in commitments:
            events = conn.execute(
                "SELECT * FROM events WHERE commitment_id=? ORDER BY occurred_at, created_at",
                (c["id"],)
            ).fetchall()
            rules: list[tuple[str, str, str, str, list[str]]] = []
            if c["due_date"] and c["status"] not in ("fulfilled", "cancelled"):
                try:
                    due = date.fromisoformat(c["due_date"][:10])
                    if due < today:
                        rules.append(("OVERDUE_COMMITMENT", "high", "Commitment is past due",
                                      f"Due date {due.isoformat()} has passed while status is '{c['status']}'.",
                                      [c["source_id"]] if c["source_id"] else []))
                except ValueError:
                    rules.append(("INVALID_DUE_DATE", "low", "Due date cannot be interpreted",
                                  f"Stored due date '{c['due_date']}' is not an ISO date.", []))
            unapproved = [e for e in events if e["event_type"].lower() in
                          ("scope_change", "amendment", "requirement_change") and not e["approved"]]
            if unapproved:
                rules.append(("UNAPPROVED_CHANGE", "critical", "Change recorded without approval",
                              f"{len(unapproved)} change event(s) are marked unapproved. Review the underlying source before accepting the change.",
                              [e["source_id"] for e in unapproved if e["source_id"]]))
            if c["status"] == "fulfilled":
                deliveries = [e for e in events if e["event_type"].lower() in
                              ("delivery", "handover", "completion", "acceptance")]
                if not deliveries:
                    rules.append(("FULFILMENT_UNSUPPORTED", "medium", "Fulfilment has no linked delivery evidence",
                                  "The commitment is marked fulfilled, but no delivery, handover, completion, or acceptance event is recorded.",
                                  [c["source_id"]] if c["source_id"] else []))
            invoice_events = [e for e in events if e["event_type"].lower() in ("invoice", "billing")]
            if invoice_events and c["value"] is not None:
                rules.append(("BILLING_REVIEW", "low", "Billing event requires value reconciliation",
                              f"{len(invoice_events)} billing event(s) exist. Compare invoice amounts with the commitment value; this engine does not infer amounts from free text.",
                              [e["source_id"] for e in invoice_events if e["source_id"]]))
            active_codes = {r[0] for r in rules}
            for code, severity, title, detail, evidence_ids in rules:
                prior = conn.execute("SELECT id FROM findings WHERE commitment_id=? AND rule_code=?",
                                     (c["id"], code)).fetchone()
                fid = f"F-{c['id']}-{code}"
                conn.execute("""
                  INSERT INTO findings(id, commitment_id, rule_code, severity, title, detail,
                    status, evidence_ids, first_seen_at, updated_at)
                  VALUES(?,?,?,?,?,?,'open',?,?,?)
                  ON CONFLICT(commitment_id, rule_code) DO UPDATE SET
                    severity=excluded.severity, title=excluded.title, detail=excluded.detail,
                    evidence_ids=excluded.evidence_ids, updated_at=excluded.updated_at
                """, (fid, c["id"], code, severity, title, detail, _json_ids(evidence_ids), stamp, stamp))
                if prior: updated += 1
                else: created += 1
            stale = conn.execute(
                "SELECT id, rule_code FROM findings WHERE commitment_id=? AND status='open'",
                (c["id"],)
            ).fetchall()
            for f in stale:
                if f["rule_code"] not in active_codes:
                    conn.execute("UPDATE findings SET status='resolved', updated_at=? WHERE id=?",
                                 (stamp, f["id"]))
                    updated += 1
    return {"created": created, "updated": updated}

def graph_data() -> dict[str, Any]:
    import json
    from .db import connect
    with connect() as conn:
        commitments = [dict(r) for r in conn.execute("SELECT * FROM commitments ORDER BY created_at DESC")]
        evidence = [dict(r) for r in conn.execute("SELECT id, filename, media_type, sha256, byte_size, created_at FROM evidence")]
        events = [dict(r) for r in conn.execute("SELECT * FROM events ORDER BY occurred_at")]
        findings = [dict(r) for r in conn.execute("SELECT * FROM findings")]
    nodes = []
    edges = []
    for c in commitments:
        nodes.append({"id": c["id"], "type": "commitment", "label": c["title"], "status": c["status"]})
        if c["source_id"]: edges.append({"source": c["id"], "target": c["source_id"], "type": "supported_by"})
    for e in evidence:
        nodes.append({"id": e["id"], "type": "evidence", "label": e["filename"]})
    for e in events:
        nodes.append({"id": e["id"], "type": "event", "label": e["event_type"] + ": " + e["description"][:72]})
        edges.append({"source": e["commitment_id"], "target": e["id"], "type": "has_event"})
        if e["source_id"]: edges.append({"source": e["id"], "target": e["source_id"], "type": "sourced_from"})
    for f in findings:
        nodes.append({"id": f["id"], "type": "finding", "label": f["title"], "severity": f["severity"]})
        edges.append({"source": f["commitment_id"], "target": f["id"], "type": "has_finding"})
        for eid in json.loads(f["evidence_ids"]):
            edges.append({"source": f["id"], "target": eid, "type": "evidenced_by"})
    return {"nodes": nodes, "edges": edges}
