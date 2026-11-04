from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DATA_DIR = Path(os.getenv("DATA_DIR", "./data")).resolve()
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "commitmentgraph.sqlite3"))).resolve()

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY, filename TEXT NOT NULL, media_type TEXT NOT NULL,
  sha256 TEXT NOT NULL UNIQUE, extracted_text TEXT NOT NULL,
  file_bytes BLOB NOT NULL DEFAULT X'', byte_size INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS commitments (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, counterparty TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '', owner TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open', due_date TEXT, value REAL,
  currency TEXT NOT NULL DEFAULT 'USD', source_id TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES evidence(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY, commitment_id TEXT NOT NULL, event_type TEXT NOT NULL,
  description TEXT NOT NULL, occurred_at TEXT NOT NULL,
  approved INTEGER NOT NULL DEFAULT 0, source_id TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(commitment_id) REFERENCES commitments(id) ON DELETE CASCADE,
  FOREIGN KEY(source_id) REFERENCES evidence(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY, commitment_id TEXT NOT NULL, rule_code TEXT NOT NULL,
  severity TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open', evidence_ids TEXT NOT NULL DEFAULT '[]',
  first_seen_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE(commitment_id, rule_code),
  FOREIGN KEY(commitment_id) REFERENCES commitments(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_commitments_status ON commitments(status);
CREATE INDEX IF NOT EXISTS idx_commitments_due ON commitments(due_date);
CREATE INDEX IF NOT EXISTS idx_events_commitment ON events(commitment_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_findings_status ON findings(status, severity);
"""

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()

def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

@contextmanager
def transaction():
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def initialize() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(evidence)")}
        if "file_bytes" not in columns:
            conn.execute("ALTER TABLE evidence ADD COLUMN file_bytes BLOB NOT NULL DEFAULT X''")
