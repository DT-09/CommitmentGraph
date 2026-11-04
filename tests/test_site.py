from fastapi.testclient import TestClient
from app.main import app


def test_public_site_and_workspace_routes():
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
