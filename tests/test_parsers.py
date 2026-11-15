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


def test_csv_rejects_invalid_status_and_date():
    with pytest.raises(ValueError, match="Invalid status"):
        parse_commitment_csv("title,status\\nTask,done\\n")
    with pytest.raises(ValueError, match="due_date"):
        parse_commitment_csv("title,due_date\\nTask,2026-02-30\\n")


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "-1"])
def test_csv_rejects_non_finite_or_negative_values(value):
    with pytest.raises(ValueError, match="finite, non-negative"):
        parse_commitment_csv(f"title,value\\nTask,{value}\\n")


def test_csv_rejects_duplicate_and_unknown_headers():
    with pytest.raises(ValueError, match="duplicate"):
        parse_commitment_csv("title,title\\nA,B\\n")
    with pytest.raises(ValueError, match="Unsupported CSV column"):
        parse_commitment_csv("title,unexpected\\nA,B\\n")


def test_csv_limits_import_size_and_currency_format():
    with pytest.raises(ValueError, match="three-letter"):
        parse_commitment_csv("title,currency\\nTask,US\\n")


def test_csv_formula_cells_are_neutralized_for_spreadsheets():
    from app.parsers import spreadsheet_safe
    assert spreadsheet_safe("=HYPERLINK(\"https://example.com\")") == "'=HYPERLINK(\"https://example.com\")"
    assert spreadsheet_safe("  @SUM(A1:A2)") == "'  @SUM(A1:A2)"
    assert spreadsheet_safe("Ordinary commitment") == "Ordinary commitment"


def test_text_upload_rejects_invalid_utf8_and_unsupported_suffix():
    with pytest.raises(ValueError, match="UTF-8"):
        extract_file("broken.txt", "text/plain", b"\\xff\\xfe")
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_file("payload.exe", "application/octet-stream", b"data")
