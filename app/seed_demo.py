from __future__ import annotations

import hashlib
from datetime import date, timedelta

from .db import initialize, transaction
from .engine import investigate, now_iso


SOURCES = [
    (
        "D-DEMO-PO",
        "SAMPLE-purchase-order.txt",
        "PURCHASE ORDER — SYNTHETIC DEMONSTRATION RECORD\n"
        "Not a real customer document.\n"
        "PO: DEMO-PO-1042\nSupplier: Northstar Components (fictional)\n"
        "Scope: revised pump assembly, inspection certificate and delivery pack.\n"
        "Commercial value: USD 18,500.\n"
        "This record is provided only to demonstrate source-linked review.\n",
    ),
    (
        "D-DEMO-CHANGE",
        "SAMPLE-scope-amendment.txt",
        "SCOPE AMENDMENT — SYNTHETIC DEMONSTRATION RECORD\n"
        "Not a real customer document.\n"
        "Reference: DEMO-AMD-07\n"
        "Proposed change: add a revised acceptance test and extend commissioning.\n"
        "Approval status in this sample: no signed approval attached.\n",
    ),
    (
        "D-DEMO-INVOICE",
        "SAMPLE-milestone-invoice.txt",
        "MILESTONE INVOICE — SYNTHETIC DEMONSTRATION RECORD\n"
        "Not a real customer document.\n"
        "Invoice: DEMO-INV-209\n"
        "Milestone: engineering completion\n"
        "Amount stated in sample: USD 4,200.\n"
        "This record does not represent an actual payable or verified discrepancy.\n",
    ),
]


def seed_demo() -> dict[str, int | bool]:
    """Insert a clearly synthetic, repeat-safe workspace only into an empty database."""
    initialize()
    stamp = now_iso()
    with transaction() as conn:
        existing = sum(
            conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("commitments", "evidence", "events", "findings")
        )
        if existing:
            return {"seeded": False, "reason": "workspace_not_empty"}

        for evidence_id, filename, content in SOURCES:
            raw = content.encode("utf-8")
            conn.execute(
                """INSERT INTO evidence
                (id,filename,media_type,sha256,extracted_text,file_bytes,byte_size,created_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                (
                    evidence_id,
                    filename,
                    "text/plain",
                    hashlib.sha256(raw).hexdigest(),
                    content,
                    raw,
                    len(raw),
                    stamp,
                ),
            )

        overdue = (date.today() - timedelta(days=14)).isoformat()
        upcoming = (date.today() + timedelta(days=10)).isoformat()
        commitments = [
            ("C-DEMO-001", "Deliver revised pump assembly", "Northstar Components (sample)",
             "Deliver the revised pump assembly with inspection certificate and delivery pack.",
             "Operations", "open", overdue, 18500.0, "USD", "D-DEMO-PO"),
            ("C-DEMO-002", "Approve revised acceptance scope", "Meridian Process (sample)",
             "Review the proposed acceptance-test and commissioning scope amendment.",
             "Project Controls", "in_progress", upcoming, 4200.0, "USD", None),
            ("C-DEMO-003", "Complete site acceptance test", "Meridian Process (sample)",
             "Complete the site acceptance test and retain documentary acceptance evidence.",
             "Field Engineering", "fulfilled", None, 4200.0, "USD", None),
            ("C-DEMO-004", "Submit engineering milestone invoice", "Northstar Components (sample)",
             "Submit and reconcile the engineering-completion milestone invoice.",
             "Finance", "in_progress", upcoming, 4200.0, "USD", None),
        ]
        for row in commitments:
            conn.execute(
                """INSERT INTO commitments
                (id,title,counterparty,description,owner,status,due_date,value,currency,source_id,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (*row, stamp, stamp),
            )

        events = [
            ("E-DEMO-001", "C-DEMO-002", "scope_change",
             "Acceptance testing and commissioning scope changed; approval is not documented in this sample.",
             "D-DEMO-CHANGE", 0),
            ("E-DEMO-002", "C-DEMO-003", "acceptance",
             "Operator recorded acceptance, but no source record is attached in this sample.",
             None, 1),
            ("E-DEMO-003", "C-DEMO-004", "invoice",
             "Milestone invoice submitted; compare the source amount with the agreed commercial record.",
             "D-DEMO-INVOICE", 1),
        ]
        for event_id, commitment_id, event_type, description, source_id, approved in events:
            conn.execute(
                """INSERT INTO events
                (id,commitment_id,event_type,description,occurred_at,approved,source_id,created_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                (event_id, commitment_id, event_type, description, stamp, approved, source_id, stamp),
            )

    findings = investigate()
    return {
        "seeded": True,
        "commitments_created": len(commitments),
        "evidence_created": len(SOURCES),
        "events_created": len(events),
        "findings_created": findings["created"],
    }


if __name__ == "__main__":
    result = seed_demo()
    if result["seeded"]:
        print("Synthetic CommitmentGraph demo workspace created.")
        print(result)
    else:
        print("Demo data was not added: the workspace already contains records.")
