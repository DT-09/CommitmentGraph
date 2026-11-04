from app import db
from app.seed_demo import seed_demo


def test_demo_seed_creates_reviewable_workspace_once(tmp_path,monkeypatch):
    monkeypatch.setattr(db,"DATA_DIR",tmp_path)
    monkeypatch.setattr(db,"DB_PATH",tmp_path/"demo.sqlite3")

    result=seed_demo()
    assert result["seeded"] is True
    assert result["commitments_created"]==4
    assert result["evidence_created"]==3
    assert result["events_created"]==3
    assert result["findings_created"]==4

    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM commitments").fetchone()[0]==4
        assert conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]==3
        assert conn.execute("SELECT COUNT(*) FROM findings WHERE status='open'").fetchone()[0]==4
        original=conn.execute("SELECT file_bytes FROM evidence WHERE id='D-DEMO-PO'").fetchone()[0]
        assert b"SYNTHETIC DEMONSTRATION RECORD" in original

    second=seed_demo()
    assert second["seeded"] is False
    assert second["reason"]=="workspace_not_empty"
