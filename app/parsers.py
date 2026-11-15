from __future__ import annotations

import csv
import hashlib
import io
import math
import re
from datetime import date
from pathlib import Path
from typing import Any

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_EXTRACTED_CHARACTERS = 2_000_000
ALLOWED_STATUSES = {"open", "in_progress", "fulfilled", "cancelled", "blocked"}
ALLOWED_TEXT_SUFFIXES = {".txt", ".md", ".log", ".csv", ".json"}
ALLOWED_SUFFIXES = ALLOWED_TEXT_SUFFIXES | {".pdf", ".docx"}


def extract_file(filename: str, media_type: str, raw: bytes) -> tuple[str, str]:
    """Extract searchable text while preserving a digest of the exact uploaded bytes."""
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds the 12 MB upload limit.")
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("Unsupported file type. Upload PDF, DOCX, TXT, MD, CSV, JSON, or LOG.")

    digest = hashlib.sha256(raw).hexdigest()
    if suffix in ALLOWED_TEXT_SUFFIXES:
        try:
            text = raw.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must use UTF-8 encoding.") from exc
    elif suffix == ".pdf":
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(raw), strict=True)
            if reader.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported.")
            if len(reader.pages) > 500:
                raise ValueError("PDF exceeds the 500-page processing limit.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("The PDF could not be read. Check that it is a valid, unencrypted PDF.") from exc
    else:
        from docx import Document
        try:
            doc = Document(io.BytesIO(raw))
            parts = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                parts.extend(" | ".join(cell.text for cell in row.cells) for row in table.rows)
            text = "\n".join(parts)
        except Exception as exc:
            raise ValueError("The DOCX file could not be read. Check that it is a valid document.") from exc

    if not text.strip():
        raise ValueError("No extractable text was found in this file.")
    return text[:MAX_EXTRACTED_CHARACTERS], digest


def parse_commitment_csv(text: str) -> list[dict[str, Any]]:
    """Parse a bounded, validated commitment register CSV."""
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise ValueError("CSV file must contain a header row.")

    headers = [str(value or "").strip().lower() for value in reader.fieldnames]
    if len(headers) != len(set(headers)):
        raise ValueError("CSV contains duplicate column names.")
    if "title" not in headers:
        raise ValueError("CSV import requires a 'title' column.")

    allowed = {"title", "counterparty", "description", "owner", "status", "due_date", "value", "currency"}
    unknown = sorted(set(headers) - allowed)
    if unknown:
        raise ValueError(f"Unsupported CSV column(s): {', '.join(unknown)}.")

    rows: list[dict[str, Any]] = []
    for line, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(f"CSV line {line} has more values than the header.")
        normalized = {
            str(key or "").strip().lower(): (value or "").strip()
            for key, value in row.items()
        }
        title = normalized.get("title", "")
        if not title:
            continue
        if len(title) > 300:
            raise ValueError(f"Title on CSV line {line} exceeds 300 characters.")

        status = normalized.get("status", "open").lower() or "open"
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"Invalid status on CSV line {line}. Use: {', '.join(sorted(ALLOWED_STATUSES))}.")

        due_date = normalized.get("due_date") or None
        if due_date:
            try:
                date.fromisoformat(due_date)
            except ValueError as exc:
                raise ValueError(f"Invalid ISO due_date on CSV line {line}; expected YYYY-MM-DD.") from exc

        raw_value = normalized.get("value") or None
        try:
            amount = float(raw_value) if raw_value else None
        except ValueError as exc:
            raise ValueError(f"Invalid numeric value on CSV line {line}.") from exc
        if amount is not None and (not math.isfinite(amount) or amount < 0):
            raise ValueError(f"Value on CSV line {line} must be a finite, non-negative number.")

        currency = (normalized.get("currency") or "USD").upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError(f"Invalid currency on CSV line {line}; use a three-letter currency code.")

        if len(rows) >= 500:
            raise ValueError("CSV import is limited to 500 commitments per file.")

        rows.append({
            "title": title,
            "counterparty": normalized.get("counterparty", ""),
            "description": normalized.get("description", ""),
            "owner": normalized.get("owner", ""),
            "status": status,
            "due_date": due_date,
            "value": amount,
            "currency": currency,
        })
    return rows


def spreadsheet_safe(value: Any) -> Any:
    """Prevent spreadsheet applications from evaluating exported text as formulas."""
    if not isinstance(value, str):
        return value
    candidate = value.lstrip(" \t\r\n")
    if candidate.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
