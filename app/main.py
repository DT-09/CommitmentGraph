from __future__ import annotations

import csv
import hashlib
import io
import os
import secrets
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Header, HTTPException, UploadFile, Depends
from fastapi.responses import FileResponse, Response, StreamingResponse
from urllib.parse import quote
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import connect, initialize, transaction
from .engine import investigate, graph_data, now_iso
from .parsers import extract_file, parse_commitment_csv, MAX_UPLOAD_BYTES

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
API_KEY = os.getenv("COMMITMENTGRAPH_API_KEY", "").strip()
app = FastAPI(title="CommitmentGraph", version="1.0.1",
              description="Evidence-linked business commitment reconstruction.",
              docs_url="/api/docs", redoc_url=None)

def authorize(x_api_key: str | None = Header(default=None)):
    if API_KEY and not secrets.compare_digest(x_api_key or "", API_KEY):
        raise HTTPException(status_code=401, detail="A valid API key is required.")
    return True

class CommitmentIn(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    counterparty: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=8000)
    owner: str = Field(default="", max_length=200)
    status: str = Field(default="open", pattern="^(open|in_progress|fulfilled|cancelled|blocked)$")
    due_date: str | None = None
    value: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    source_id: str | None = None

class EventIn(BaseModel):
    event_type: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=2, max_length=4000)
    occurred_at: str | None = None
    approved: bool = False
    source_id: str | None = None

class BundleIn(BaseModel):
    commitments: list[CommitmentIn] = Field(default_factory=list, max_length=500)
    events: list[dict[str, Any]] = Field(default_factory=list, max_length=2000)

@app.on_event("startup")
def startup():
    initialize()

@app.get("/api/health")
def health():
    return {"status": "ok", "product": "CommitmentGraph", "version": "1.0.1"}

@app.get("/api/overview", dependencies=[Depends(authorize)])
def overview():
    with connect() as conn:
        commitments = conn.execute("SELECT COUNT(*) n FROM commitments").fetchone()["n"]
        open_count = conn.execute("SELECT COUNT(*) n FROM commitments WHERE status IN ('open','in_progress','blocked')").fetchone()["n"]
        evidence = conn.execute("SELECT COUNT(*) n FROM evidence").fetchone()["n"]
        events = conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"]
        findings = conn.execute("SELECT COUNT(*) n FROM findings WHERE status='open'").fetchone()["n"]
        critical = conn.execute("SELECT COUNT(*) n FROM findings WHERE status='open' AND severity='critical'").fetchone()["n"]
        recent = [dict(r) for r in conn.execute("""
          SELECT f.*, c.title commitment_title FROM findings f
          JOIN commitments c ON c.id=f.commitment_id
          WHERE f.status='open' ORDER BY CASE f.severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, f.updated_at DESC LIMIT 8
        """)]
    return {"commitments": commitments, "open_commitments": open_count, "evidence": evidence,
            "events": events, "open_findings": findings, "critical_findings": critical,
            "recent_findings": recent}

@app.get("/api/commitments", dependencies=[Depends(authorize)])
def list_commitments():
    with connect() as conn:
        rows = conn.execute("""
          SELECT c.*, (SELECT COUNT(*) FROM events e WHERE e.commitment_id=c.id) event_count,
          (SELECT COUNT(*) FROM findings f WHERE f.commitment_id=c.id AND f.status='open') finding_count
          FROM commitments c ORDER BY c.updated_at DESC
        """).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/commitments", status_code=201, dependencies=[Depends(authorize)])
def create_commitment(data: CommitmentIn):
    cid, stamp = "C-" + uuid.uuid4().hex[:10].upper(), now_iso()
    with transaction() as conn:
        if data.source_id and not conn.execute("SELECT 1 FROM evidence WHERE id=?", (data.source_id,)).fetchone():
            raise HTTPException(404, "Source evidence was not found.")
        conn.execute("""INSERT INTO commitments
          (id,title,counterparty,description,owner,status,due_date,value,currency,source_id,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
          (cid,data.title,data.counterparty,data.description,data.owner,data.status,data.due_date,
           data.value,data.currency.upper(),data.source_id,stamp,stamp))
    return {"id": cid, "created": True}

@app.patch("/api/commitments/{commitment_id}", dependencies=[Depends(authorize)])
def update_commitment(commitment_id: str, data: CommitmentIn):
    with transaction() as conn:
        if data.source_id and not conn.execute("SELECT 1 FROM evidence WHERE id=?", (data.source_id,)).fetchone():
            raise HTTPException(404, "Source evidence was not found.")
        cur = conn.execute("""UPDATE commitments SET title=?,counterparty=?,description=?,owner=?,status=?,
          due_date=?,value=?,currency=?,source_id=?,updated_at=? WHERE id=?""",
          (data.title,data.counterparty,data.description,data.owner,data.status,data.due_date,data.value,
           data.currency.upper(),data.source_id,now_iso(),commitment_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Commitment not found.")
    return {"id": commitment_id, "updated": True}

@app.get("/api/commitments/{commitment_id}", dependencies=[Depends(authorize)])
def commitment_detail(commitment_id: str):
    with connect() as conn:
        c = conn.execute("SELECT * FROM commitments WHERE id=?", (commitment_id,)).fetchone()
        if not c: raise HTTPException(404, "Commitment not found.")
        events = [dict(r) for r in conn.execute("SELECT * FROM events WHERE commitment_id=? ORDER BY occurred_at DESC", (commitment_id,))]
        findings = [dict(r) for r in conn.execute("SELECT * FROM findings WHERE commitment_id=? ORDER BY updated_at DESC", (commitment_id,))]
    return {"commitment": dict(c), "events": events, "findings": findings}

@app.post("/api/commitments/{commitment_id}/events", status_code=201, dependencies=[Depends(authorize)])
def add_event(commitment_id: str, data: EventIn):
    eid = "E-" + uuid.uuid4().hex[:10].upper()
    occurred = data.occurred_at or now_iso()
    with transaction() as conn:
        if not conn.execute("SELECT 1 FROM commitments WHERE id=?", (commitment_id,)).fetchone():
            raise HTTPException(404, "Commitment not found.")
        if data.source_id and not conn.execute("SELECT 1 FROM evidence WHERE id=?", (data.source_id,)).fetchone():
            raise HTTPException(404, "Source evidence was not found.")
        conn.execute("""INSERT INTO events(id,commitment_id,event_type,description,occurred_at,approved,source_id,created_at)
          VALUES(?,?,?,?,?,?,?,?)""",
          (eid,commitment_id,data.event_type.strip().lower(),data.description,occurred,int(data.approved),data.source_id,now_iso()))
    return {"id": eid, "created": True}

@app.get("/api/evidence", dependencies=[Depends(authorize)])
def list_evidence():
    with connect() as conn:
        rows = conn.execute("SELECT id,filename,media_type,sha256,byte_size,created_at FROM evidence ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

@app.get("/api/evidence/{evidence_id}", dependencies=[Depends(authorize)])
def evidence_detail(evidence_id: str):
    with connect() as conn:
        row = conn.execute("""SELECT id,filename,media_type,sha256,extracted_text,byte_size,created_at,
          length(file_bytes) AS original_size FROM evidence WHERE id=?""", (evidence_id,)).fetchone()
    if not row: raise HTTPException(404, "Evidence not found.")
    result = dict(row)
    result["original_available"] = bool(result.pop("original_size"))
    return result

@app.get("/api/evidence/{evidence_id}/original", dependencies=[Depends(authorize)])
def download_evidence_original(evidence_id: str):
    with connect() as conn:
        row = conn.execute("SELECT filename,media_type,file_bytes,sha256 FROM evidence WHERE id=?", (evidence_id,)).fetchone()
    if not row: raise HTTPException(404, "Evidence not found.")
    if not row["file_bytes"]:
        raise HTTPException(410, "The original file is unavailable for this legacy evidence record.")
    raw = bytes(row["file_bytes"])
    if not secrets.compare_digest(hashlib.sha256(raw).hexdigest(), row["sha256"]):
        raise HTTPException(500, "Stored source bytes failed SHA-256 integrity verification.")
    filename = quote(Path(row["filename"]).name, safe="")
    return Response(content=raw, media_type=row["media_type"] or "application/octet-stream",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"})

@app.post("/api/evidence", status_code=201, dependencies=[Depends(authorize)])
async def upload_evidence(file: UploadFile = File(...)):
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File exceeds the 12 MB upload limit.")
    try:
        extracted, digest = extract_file(file.filename or "upload", file.content_type or "application/octet-stream", raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    eid = "D-" + uuid.uuid4().hex[:10].upper()
    with transaction() as conn:
        existing = conn.execute("SELECT id FROM evidence WHERE sha256=?", (digest,)).fetchone()
        if existing: return {"id": existing["id"], "duplicate": True}
        conn.execute("""INSERT INTO evidence(id,filename,media_type,sha256,extracted_text,file_bytes,byte_size,created_at)
          VALUES(?,?,?,?,?,?,?,?)""",
          (eid,file.filename or "upload",file.content_type or "application/octet-stream",digest,extracted,raw,len(raw),now_iso()))
    return {"id": eid, "duplicate": False, "characters_extracted": len(extracted), "sha256": digest}

@app.post("/api/import/csv", dependencies=[Depends(authorize)])
async def import_csv(file: UploadFile = File(...)):
    raw = await file.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024: raise HTTPException(413, "CSV exceeds 2 MB.")
    try:
        rows = parse_commitment_csv(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(400, str(exc)) from exc
    stamp, created = now_iso(), 0
    with transaction() as conn:
        for item in rows:
            cid = "C-" + uuid.uuid4().hex[:10].upper()
            conn.execute("""INSERT INTO commitments
              (id,title,counterparty,description,owner,status,due_date,value,currency,created_at,updated_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
              (cid,item["title"],item["counterparty"],item["description"],item["owner"],
               item["status"],item["due_date"],item["value"],item["currency"].upper(),stamp,stamp))
            created += 1
    return {"created": created}

@app.post("/api/import/bundle", dependencies=[Depends(authorize)])
def import_bundle(data: BundleIn):
    stamp, ids = now_iso(), {}
    with transaction() as conn:
        for item in data.commitments:
            cid = "C-" + uuid.uuid4().hex[:10].upper()
            if item.source_id and not conn.execute("SELECT 1 FROM evidence WHERE id=?", (item.source_id,)).fetchone():
                raise HTTPException(404, "Bundle references unknown source evidence.")
            conn.execute("""INSERT INTO commitments
              (id,title,counterparty,description,owner,status,due_date,value,currency,source_id,created_at,updated_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
              (cid,item.title,item.counterparty,item.description,item.owner,item.status,item.due_date,
               item.value,item.currency.upper(),item.source_id,stamp,stamp))
            ids[item.title] = cid
        for item in data.events:
            title = item.get("commitment_title")
            cid = item.get("commitment_id") or ids.get(title)
            if not cid or not conn.execute("SELECT 1 FROM commitments WHERE id=?", (cid,)).fetchone():
                raise HTTPException(400, f"Event references unknown commitment: {title or cid}")
            source_id = item.get("source_id")
            if source_id and not conn.execute("SELECT 1 FROM evidence WHERE id=?", (source_id,)).fetchone():
                raise HTTPException(404, "Bundle references unknown source evidence.")
            conn.execute("""INSERT INTO events(id,commitment_id,event_type,description,occurred_at,approved,source_id,created_at)
              VALUES(?,?,?,?,?,?,?,?)""",
              ("E-"+uuid.uuid4().hex[:10].upper(),cid,str(item.get("event_type","note")).lower(),
               str(item.get("description","Imported event")),str(item.get("occurred_at") or stamp),
               int(bool(item.get("approved",False))),source_id,stamp))
    return {"commitments_created": len(ids), "events_created": len(data.events), "ids": ids}

@app.post("/api/investigate", dependencies=[Depends(authorize)])
def run_investigation():
    return investigate()

@app.get("/api/findings", dependencies=[Depends(authorize)])
def list_findings(status: str = "open"):
    if status not in ("open","resolved","all"): raise HTTPException(400, "status must be open, resolved, or all")
    query = """SELECT f.*,c.title commitment_title,c.counterparty FROM findings f
      JOIN commitments c ON c.id=f.commitment_id"""
    if status != "all": query += " WHERE f.status=?"
    query += " ORDER BY CASE f.severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, f.updated_at DESC"
    with connect() as conn:
        rows = conn.execute(query, () if status=="all" else (status,)).fetchall()
    return [dict(r) for r in rows]

@app.patch("/api/findings/{finding_id}/resolve", dependencies=[Depends(authorize)])
def resolve_finding(finding_id: str):
    with transaction() as conn:
        cur = conn.execute("UPDATE findings SET status='resolved',updated_at=? WHERE id=?",
                           (now_iso(),finding_id))
        if not cur.rowcount: raise HTTPException(404, "Finding not found.")
    return {"id": finding_id, "status": "resolved"}

@app.get("/api/graph", dependencies=[Depends(authorize)])
def get_graph():
    return graph_data()

@app.get("/api/reports/findings.csv", dependencies=[Depends(authorize)])
def findings_csv():
    with connect() as conn:
        rows = conn.execute("""SELECT f.id,f.severity,f.rule_code,f.title,f.detail,f.status,
          c.id commitment_id,c.title commitment_title,c.counterparty,f.evidence_ids,f.first_seen_at,f.updated_at
          FROM findings f JOIN commitments c ON c.id=f.commitment_id ORDER BY f.severity,f.first_seen_at""").fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["finding_id","severity","rule_code","finding","detail","status","commitment_id","commitment","counterparty","evidence_ids","first_seen_at","updated_at"])
    for row in rows: writer.writerow(list(row))
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
      headers={"Content-Disposition":"attachment; filename=commitmentgraph-findings.csv"})

@app.get("/api/reports/commitments.csv", dependencies=[Depends(authorize)])
def commitments_csv():
    with connect() as conn:
        rows = conn.execute("SELECT id,title,counterparty,description,owner,status,due_date,value,currency,source_id,created_at,updated_at FROM commitments ORDER BY created_at").fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id","title","counterparty","description","owner","status","due_date","value","currency","source_id","created_at","updated_at"])
    for row in rows: writer.writerow(list(row))
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
      headers={"Content-Disposition":"attachment; filename=commitmentgraph-commitments.csv"})

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC / "marketing.html")

@app.get("/workspace", include_in_schema=False)
def workspace():
    return FileResponse(STATIC / "index.html")

app.mount("/static", StaticFiles(directory=STATIC), name="static")
