"""Tests for the attachment processing service (Phase 3)."""

import io

import pytest

from app.services.attachment_service.processor import (
    AttachmentText,
    combine_email_and_attachments,
    extract_attachment_text,
    extract_docx_text,
    extract_pdf_text,
)


def test_extract_pdf_text():
    """Test PDF text extraction with a minimal PDF."""
    # Create a minimal valid PDF manually
    pdf_bytes = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
178
%%EOF"""
    # This minimal PDF has no text content, so extraction should return empty text
    result = extract_pdf_text(pdf_bytes, "test.pdf")
    assert isinstance(result, AttachmentText)
    assert result.filename == "test.pdf"
    assert result.content_type == "application/pdf"
    assert result.pages is not None


def test_extract_docx_text():
    """Test DOCX text extraction."""
    from docx import Document

    doc = Document()
    doc.add_paragraph("Placement Selections - TechNova Solutions")
    doc.add_paragraph("Name: Arjun Mehta")
    doc.add_paragraph("Reg No: 22CS014")
    doc.add_paragraph("Branch: CSE")
    doc.add_paragraph("Role: Software Engineer")
    doc.add_paragraph("CTC: 12 LPA")

    buf = io.BytesIO()
    doc.save(buf)
    data = buf.getvalue()

    result = extract_docx_text(data, "selection.docx")
    assert isinstance(result, AttachmentText)
    assert result.filename == "selection.docx"
    assert "TechNova Solutions" in result.text
    assert "Arjun Mehta" in result.text
    assert "22CS014" in result.text
    assert "CSE" in result.text
    assert "Software Engineer" in result.text
    assert "12 LPA" in result.text


def test_extract_docx_with_table():
    """Test DOCX text extraction including table content."""
    from docx import Document

    doc = Document()
    doc.add_paragraph("Placement Results")
    table = doc.add_table(rows=2, cols=3)
    table.rows[0].cells[0].text = "Student Name"
    table.rows[0].cells[1].text = "Branch"
    table.rows[0].cells[2].text = "CTC"
    table.rows[1].cells[0].text = "Sneha Reddy"
    table.rows[1].cells[1].text = "IT"
    table.rows[1].cells[2].text = "10 LPA"

    buf = io.BytesIO()
    doc.save(buf)
    data = buf.getvalue()

    result = extract_docx_text(data, "results.docx")
    assert "Sneha Reddy" in result.text
    assert "IT" in result.text
    assert "10 LPA" in result.text


def test_extract_attachment_text_dispatch():
    """Test that extract_attachment_text dispatches correctly."""
    # PDF - even a minimal PDF should return an AttachmentText object
    result = extract_attachment_text("file.pdf", "application/pdf", b"%PDF-1.4")
    assert result is not None
    assert result.content_type == "application/pdf"
    assert result.filename == "file.pdf"

    # DOCX
    from docx import Document
    doc = Document()
    doc.add_paragraph("Hello World")
    buf = io.BytesIO()
    doc.save(buf)
    result = extract_attachment_text("file.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", buf.getvalue())
    assert result is not None
    assert "Hello World" in result.text

    # TXT
    result = extract_attachment_text("file.txt", "text/plain", b"Hello text")
    assert result is not None
    assert result.text == "Hello text"

    # Unsupported
    result = extract_attachment_text("file.exe", "application/x-msdownload", b"binary")
    assert result is None

    # Legacy .doc
    result = extract_attachment_text("file.doc", "application/msword", b"binary")
    assert result is None


def test_combine_no_attachments():
    """Test combining with no attachments returns email body with header."""
    combined = combine_email_and_attachments("Just email body", [])
    assert "=== EMAIL BODY ===" in combined
    assert "Just email body" in combined


def test_combine_email_and_attachments():
    """Test combining email body with attachment text."""
    email_body = "Name: Arjun Mehta\nCTC: 12 LPA"
    att1 = AttachmentText(
        filename="results.pdf",
        content_type="application/pdf",
        size=100,
        text="Name: Sneha Reddy\nCTC: 10 LPA",
        pages=1,
    )
    att2 = AttachmentText(
        filename="empty.pdf",
        content_type="application/pdf",
        size=50,
        text="",
        pages=1,
    )

    combined = combine_email_and_attachments(email_body, [att1, att2])

    assert "=== EMAIL BODY ===" in combined
    assert "Name: Arjun Mehta" in combined
    assert "=== ATTACHMENT: results.pdf ===" in combined
    assert "Name: Sneha Reddy" in combined
    assert "=== ATTACHMENT: empty.pdf ===" not in combined  # empty text skipped


def test_combine_no_attachments():
    """Test combining with no attachments returns email body with header."""
    combined = combine_email_and_attachments("Just email body", [])
    assert "=== EMAIL BODY ===" in combined
    assert "Just email body" in combined


def test_combine_no_email_body():
    """Test combining with no email body."""
    att = AttachmentText(
        filename="results.pdf",
        content_type="application/pdf",
        size=100,
        text="Attachment content",
        pages=1,
    )
    combined = combine_email_and_attachments(None, [att])
    assert "=== ATTACHMENT: results.pdf ===" in combined
    assert "Attachment content" in combined
    assert "=== EMAIL BODY ===" not in combined
