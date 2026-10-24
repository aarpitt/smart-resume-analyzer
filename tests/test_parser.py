"""
Unit tests for ResumeParser module.
Verifies PDF and DOCX parsing, contact extraction, section segmentation, and error handling.
"""

import os
import pytest
from app.parser import ResumeParser, ParserError

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_resumes")


def test_parser_pdf_extraction():
    pdf_path = os.path.join(SAMPLES_DIR, "sample_data_analyst.pdf")
    assert os.path.exists(pdf_path), "Sample PDF must exist"

    parser = ResumeParser(pdf_path)
    result = parser.parse()

    assert result["filename"] == "sample_data_analyst.pdf"
    assert result["word_count"] > 100
    assert "Maya Patel" in result["raw_text"]
    assert result["contact_info"]["email"] == "maya.patel.analytics@example.com"
    assert result["contact_info"]["phone"] is not None
    assert "linkedin.com" in result["contact_info"]["linkedin"]
    assert "github.com" in result["contact_info"]["github"]

    # Section detection
    detected = result["detected_sections"]
    assert "education" in detected
    assert "skills" in detected
    assert "experience" in detected
    assert "projects" in detected


def test_parser_docx_extraction():
    docx_path = os.path.join(SAMPLES_DIR, "sample_ai_engineer.docx")
    assert os.path.exists(docx_path), "Sample DOCX must exist"

    parser = ResumeParser(docx_path)
    result = parser.parse()

    assert result["filename"] == "sample_ai_engineer.docx"
    assert result["word_count"] > 100
    assert "Alex Chen" in result["raw_text"]
    assert result["contact_info"]["email"] == "alex.chen.ai@example.com"
    assert result["contact_info"]["phone"] is not None
    assert result["contact_info"]["linkedin"] is not None
    assert result["contact_info"]["github"] is not None

    detected = result["detected_sections"]
    assert "education" in detected
    assert "skills" in detected
    assert "experience" in detected
    assert "projects" in detected


def test_parser_unsupported_format(tmp_path):
    invalid_file = tmp_path / "resume.txt"
    invalid_file.write_text("Plain text resume")

    with pytest.raises(ParserError) as exc_info:
        ResumeParser(str(invalid_file))
    assert "Unsupported file format" in str(exc_info.value)


def test_parser_empty_file(tmp_path):
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"")

    parser = ResumeParser(str(empty_pdf))
    with pytest.raises(ParserError) as exc_info:
        parser.parse()
    assert "empty" in str(exc_info.value).lower()


def test_parser_scanned_or_short_file(tmp_path):
    short_docx = tmp_path / "short.docx"
    # Create empty docx
    from docx import Document
    doc = Document()
    doc.add_paragraph("Too brief")
    doc.save(str(short_docx))

    parser = ResumeParser(str(short_docx))
    with pytest.raises(ParserError) as exc_info:
        parser.parse()
    assert "insufficient readable text" in str(exc_info.value).lower()
