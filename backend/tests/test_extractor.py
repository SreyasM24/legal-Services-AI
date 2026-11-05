"""
Tests for Document Extraction Engine (PDF, DOCX, TXT, security, errors).
"""

import pytest
from app.services.extractor import (
    extract_document,
    sanitize_filename,
    validate_file_metadata,
    ExtractionError,
    MAX_FILE_SIZE_BYTES,
)


def test_sanitize_filename():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\Windows\\System32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("Legal Contract #1 (Final).pdf") == "Legal Contract _1 (Final).pdf"
    assert sanitize_filename("") == "untitled_document.txt"


def test_validate_file_metadata_errors():
    with pytest.raises(ExtractionError, match="Document is empty"):
        validate_file_metadata("test.txt", 0)

    with pytest.raises(ExtractionError, match="exceeds maximum allowed limit"):
        validate_file_metadata("large.pdf", MAX_FILE_SIZE_BYTES + 1)

    with pytest.raises(ExtractionError, match="Unsupported file format"):
        validate_file_metadata("malicious.exe", 1024)

    with pytest.raises(ExtractionError, match="Unsupported file format"):
        validate_file_metadata("data.csv", 500)


def test_extract_txt_success(sample_contract_text):
    raw_bytes = sample_contract_text.encode("utf-8")
    full_text, sections, meta = extract_document("nda_contract.txt", raw_bytes)

    assert meta["file_type"] == "txt"
    assert meta["word_count"] > 100
    assert len(sections) > 5
    assert "CONFIDENTIALITY" in full_text
    assert sections[0].index == 0
    assert sections[0].page_number >= 1


def test_extract_txt_latin1_encoding():
    latin1_text = "This contract costs £500 or ¥10000 with naïve clauses."
    raw_bytes = latin1_text.encode("latin-1")
    full_text, sections, meta = extract_document("latin1.txt", raw_bytes)

    assert meta["file_type"] == "txt"
    assert "£500" in full_text
    assert "naïve" in full_text


def test_extract_pdf_success(sample_pdf_bytes):
    full_text, sections, meta = extract_document("agreement.pdf", sample_pdf_bytes)

    assert meta["file_type"] == "pdf"
    assert meta["page_count"] == 1
    assert "CONFIDENTIALITY" in full_text
    assert len(sections) == 1
    assert sections[0].page_number == 1


def test_scanned_pdf_error(empty_pdf_bytes):
    with pytest.raises(ExtractionError, match="Scanned PDFs require Optical Character Recognition"):
        extract_document("scanned_empty.pdf", empty_pdf_bytes)


def test_extract_docx_success(sample_docx_bytes):
    full_text, sections, meta = extract_document("agreement.docx", sample_docx_bytes)

    assert meta["file_type"] == "docx"
    assert "Master Services Agreement" in full_text
    assert "Termination" in full_text
    assert len(sections) >= 3


def test_corrupted_pdf_error():
    garbage = b"This is not a real PDF file header."
    with pytest.raises(ExtractionError, match="Invalid or corrupted PDF file"):
        extract_document("broken.pdf", garbage)


def test_corrupted_docx_error():
    garbage = b"PK\x03\x04corrupted docx stream"
    with pytest.raises(ExtractionError, match="Invalid or corrupted DOCX file"):
        extract_document("broken.docx", garbage)
