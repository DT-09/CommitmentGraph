from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from typing import Any

MAX_UPLOAD_BYTES = 12 * 1024 * 1024

def extract_file(filename: str, media_type: str, raw: bytes) -> tuple[str, str]:
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds the 12 MB upload limit.")
    suffix = Path(filename).suffix.lower()
    digest = hashlib.sha256(raw).hexdigest()
    if suffix in (".txt", ".md", ".log", ".csv", ".json"):
        text = raw.decode("utf-8-sig", errors="replace")
    elif suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        from docx import Document
        doc = Document(io.BytesIO(raw))
        text = "\n".join(p.text for p in doc.paragraphs)
        for table in doc.tables:
            text += "\n" + "\n".join(" | ".join(cell.text for cell in row.cells) for row in table.rows)
    else:
        raise ValueError("Unsupported file type. Upload PDF, DOCX, TXT, MD, CSV, JSON, or LOG.")
    if not text.strip():
        raise ValueError("No extractable text was found in this file.")
    return text[:2_000_000], digest

def parse_commitment_csv(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    required = {"title"}
    fields = {str(x or "").strip().lower() for x in (reader.fieldnames or [])}
    if not required.issubset(fields):
        raise ValueError("CSV import requires a 'title' column.")
    rows = []
    for line, row in enumerate(reader, start=2):
        normalized = {str(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        if not normalized.get("title"):
            continue
        value = normalized.get("value") or None
        try:
            amount = float(value) if value else None
        except ValueError as exc:
            raise ValueError(f"Invalid numeric value on CSV line {line}.") from exc
        rows.append({
            "title": normalized["title"],
            "counterparty": normalized.get("counterparty", ""),
            "description": normalized.get("description", ""),
            "owner": normalized.get("owner", ""),
            "status": normalized.get("status", "open") or "open",
            "due_date": normalized.get("due_date") or None,
            "value": amount,
            "currency": normalized.get("currency", "USD") or "USD",
        })
    return rows
