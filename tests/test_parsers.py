import pytest
from app.parsers import extract_file, parse_commitment_csv

def test_csv_import_normalizes_optional_fields():
    rows=parse_commitment_csv("title,counterparty,due_date,value\nDeliver pump,Northstar,2026-12-01,1250.50\n")
    assert rows[0]["title"]=="Deliver pump"
    assert rows[0]["value"]==1250.50
    assert rows[0]["status"]=="open"

def test_csv_requires_title_column():
    with pytest.raises(ValueError,match="title"):
        parse_commitment_csv("name,owner\nTask,A\n")

def test_evidence_hash_is_stable():
    text,digest=extract_file("source.txt","text/plain",b"Approved delivery date: Friday")
    assert "Friday" in text
    assert len(digest)==64
