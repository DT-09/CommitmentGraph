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
