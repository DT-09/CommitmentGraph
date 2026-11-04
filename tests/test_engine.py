from datetime import date
import json
from app import db
from app.engine import investigate, graph_data, now_iso

def seed(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")
    db.initialize()
    stamp = now_iso()
    with db.transaction() as conn:
        conn.execute("""INSERT INTO commitments
          (id,title,counterparty,status,due_date,currency,created_at,updated_at)
          VALUES('C-1','Deliver prototype','Northstar','open','2025-01-01','USD',?,?)""",(stamp,stamp))
        conn.execute("""INSERT INTO evidence(id,filename,media_type,sha256,extracted_text,byte_size,created_at)
          VALUES('D-1','amendment.txt','text/plain','abc123','Changed delivery scope',22,?)""",(stamp,))
        conn.execute("""INSERT INTO events(id,commitment_id,event_type,description,occurred_at,approved,source_id,created_at)
          VALUES('E-1','C-1','scope_change','Delivery scope changed',?,0,'D-1',?)""",(stamp,stamp))

def test_investigation_creates_explainable_findings(tmp_path,monkeypatch):
    seed(tmp_path,monkeypatch)
    result=investigate(today=date(2026,1,1))
    assert result["created"] == 2
    with db.connect() as conn:
        rows=conn.execute("SELECT rule_code,severity,evidence_ids FROM findings ORDER BY rule_code").fetchall()
    found={r["rule_code"]:r for r in rows}
    assert found["OVERDUE_COMMITMENT"]["severity"]=="high"
    assert json.loads(found["UNAPPROVED_CHANGE"]["evidence_ids"])==["D-1"]

def test_investigation_is_idempotent(tmp_path,monkeypatch):
    seed(tmp_path,monkeypatch)
    investigate(today=date(2026,1,1))
    result=investigate(today=date(2026,1,1))
    assert result["created"]==0
    assert result["updated"]==2

def test_reviewed_findings_remain_reviewed_when_condition_persists(tmp_path,monkeypatch):
    seed(tmp_path,monkeypatch)
    investigate(today=date(2026,1,1))
    with db.transaction() as conn:
        conn.execute("UPDATE findings SET status='resolved'")
    investigate(today=date(2026,1,1))
    with db.connect() as conn:
        statuses=[r["status"] for r in conn.execute("SELECT status FROM findings")]
    assert statuses==["resolved","resolved"]

def test_graph_connects_commitment_event_evidence_and_finding(tmp_path,monkeypatch):
    seed(tmp_path,monkeypatch)
    investigate(today=date(2026,1,1))
    graph=graph_data()
    types={n["type"] for n in graph["nodes"]}
    assert types=={"commitment","event","evidence","finding"}
    assert any(e["type"]=="evidenced_by" for e in graph["edges"])


def test_fulfilment_event_without_source_does_not_count_as_evidence(tmp_path,monkeypatch):
    seed(tmp_path,monkeypatch)
    stamp=now_iso()
    with db.transaction() as conn:
        conn.execute("""INSERT INTO commitments
          (id,title,status,currency,created_at,updated_at)
          VALUES('C-2','Complete commissioning','fulfilled','USD',?,?)""",(stamp,stamp))
        conn.execute("""INSERT INTO events
          (id,commitment_id,event_type,description,occurred_at,approved,created_at)
          VALUES('E-2','C-2','acceptance','Customer accepted the work',?,1,?)""",(stamp,stamp))
    investigate(today=date(2026,1,1))
    with db.connect() as conn:
        finding=conn.execute("SELECT rule_code FROM findings WHERE commitment_id='C-2'").fetchone()
    assert finding["rule_code"]=="FULFILMENT_UNSUPPORTED"
    with db.transaction() as conn:
        conn.execute("UPDATE events SET source_id='D-1' WHERE id='E-2'")
    investigate(today=date(2026,1,1))
    with db.connect() as conn:
        finding=conn.execute("SELECT status FROM findings WHERE commitment_id='C-2' AND rule_code='FULFILMENT_UNSUPPORTED'").fetchone()
    assert finding["status"]=="resolved"


def test_approval_flag_without_linked_source_is_still_a_review_signal(tmp_path,monkeypatch):
    seed(tmp_path,monkeypatch)
    stamp=now_iso()
    with db.transaction() as conn:
        conn.execute("""INSERT INTO commitments
          (id,title,status,currency,created_at,updated_at)
          VALUES('C-2','Approve revised specification','open','USD',?,?)""",(stamp,stamp))
        conn.execute("""INSERT INTO events
          (id,commitment_id,event_type,description,occurred_at,approved,created_at)
          VALUES('E-2','C-2','amendment','Specification amended',?,1,?)""",(stamp,stamp))
    investigate(today=date(2026,1,1))
    with db.connect() as conn:
        finding=conn.execute("SELECT rule_code FROM findings WHERE commitment_id='C-2'").fetchone()
    assert finding["rule_code"]=="UNAPPROVED_CHANGE"
