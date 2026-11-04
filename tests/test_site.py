from fastapi.testclient import TestClient
from app import db
from app.main import app


def test_public_site_and_workspace_routes(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "site.sqlite3")

    with TestClient(app) as client:
        landing = client.get("/")
        workspace = client.get("/workspace")
        stylesheet = client.get("/static/site.css")

    assert landing.status_code == 200
    assert "Know what was promised" in landing.text
    assert workspace.status_code == 200
    assert "Commitment overview" in workspace.text
    assert stylesheet.status_code == 200
    assert "--bg:#101713" in stylesheet.text
