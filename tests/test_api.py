from fastapi.testclient import TestClient
from app import db
from app.main import app

def test_health_and_commitment_flow(tmp_path,monkeypatch):
    monkeypatch.setattr(db,"DATA_DIR",tmp_path)
    monkeypatch.setattr(db,"DB_PATH",tmp_path/"api.sqlite3")
    db.initialize()
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"]=="ok"
        created=client.post("/api/commitments",json={"title":"Deliver signed test report","counterparty":"Northstar"})
        assert created.status_code==201
        cid=created.json()["id"]
        event=client.post(f"/api/commitments/{cid}/events",json={
            "event_type":"scope_change","description":"Acceptance criteria amended","approved":False
        })
        assert event.status_code==201
        result=client.post("/api/investigate")
        assert result.status_code==200
        findings=client.get("/api/findings").json()
        assert any(f["rule_code"]=="UNAPPROVED_CHANGE" for f in findings)

def test_csv_report_download(tmp_path,monkeypatch):
    monkeypatch.setattr(db,"DATA_DIR",tmp_path)
    monkeypatch.setattr(db,"DB_PATH",tmp_path/"report.sqlite3")
    db.initialize()
    with TestClient(app) as client:
        r=client.get("/api/reports/commitments.csv")
        assert r.status_code==200
        assert "text/csv" in r.headers["content-type"]
        assert "title" in r.text


def test_uploaded_evidence_preserves_original_bytes_and_hides_blob_from_json(tmp_path,monkeypatch):
    monkeypatch.setattr(db,"DATA_DIR",tmp_path)
    monkeypatch.setattr(db,"DB_PATH",tmp_path/"evidence.sqlite3")
    db.initialize()
    source=b"Signed delivery note\nAccepted quantity: 12"
    with TestClient(app) as client:
        uploaded=client.post("/api/evidence",files={"file":("delivery-note.txt",source,"text/plain")})
        assert uploaded.status_code==201
        evidence_id=uploaded.json()["id"]
        detail=client.get(f"/api/evidence/{evidence_id}")
        assert detail.status_code==200
        assert detail.json()["original_available"] is True
        assert "file_bytes" not in detail.json()
        download=client.get(f"/api/evidence/{evidence_id}/original")
        assert download.status_code==200
        assert download.content==source
        assert "delivery-note.txt" in download.headers["content-disposition"]


def test_legacy_evidence_without_original_returns_gone(tmp_path,monkeypatch):
    monkeypatch.setattr(db,"DATA_DIR",tmp_path)
    monkeypatch.setattr(db,"DB_PATH",tmp_path/"legacy.sqlite3")
    db.initialize()
    stamp="2026-01-01T00:00:00+00:00"
    with db.transaction() as conn:
        conn.execute("""INSERT INTO evidence(id,filename,media_type,sha256,extracted_text,byte_size,created_at)
          VALUES('D-OLD','old.txt','text/plain','legacyhash','Extracted only',14,?)""",(stamp,))
    with TestClient(app) as client:
        detail=client.get("/api/evidence/D-OLD")
        assert detail.json()["original_available"] is False
        response=client.get("/api/evidence/D-OLD/original")
        assert response.status_code==410
