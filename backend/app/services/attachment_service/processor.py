"""Extract text from PDF and DOCX attachments (Phase 3).

Supports:
    - PDF via pdfplumber (falls back to PyPDF2 if unavailable)
    - DOCX via python-docx

Extracted text is returned alongside metadata so it can be fed into the
placement extraction engine together with the email body.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("placementsync")


@dataclass
class AttachmentText:
    filename: str
    content_type: str
    size: int
    text: str
    pages: int | None = None


def extract_pdf_text(data: bytes, filename: str = "document.pdf") -> AttachmentText:
    """Extract text from a PDF byte stream using pdfplumber.

    Returns an AttachmentText with empty text if the PDF cannot be parsed,
    rather than raising, so that a corrupt attachment does not fail the whole
    email processing pipeline.
    """
    try:
        import pdfplumber
    except ImportError:  # pragma: no cover - fallback path
        return _extract_pdf_text_pypdf2(data, filename)

    try:
        pages_text: list[str] = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                try:
                    pages_text.append(page.extract_text() or "")
                except Exception:
                    pages_text.append("")

        text = "\n".join(pages_text).strip()
        return AttachmentText(
            filename=filename,
            content_type="application/pdf",
            size=len(data),
            text=text,
            pages=page_count,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to parse PDF %s: %s", filename, exc)
        return AttachmentText(
            filename=filename,
            content_type="application/pdf",
            size=len(data),
            text="",
            pages=None,
        )


def _extract_pdf_text_pypdf2(data: bytes, filename: str) -> AttachmentText:
    """Fallback PDF extraction using PyPDF2."""
    try:
        import PyPDF2
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "No PDF library available. Install pdfplumber or PyPDF2."
        ) from exc

    reader = PyPDF2.PdfReader(io.BytesIO(data))
    pages_text: list[str] = []
    for page in reader.pages:
        try:
            pages_text.append(page.extract_text() or "")
        except Exception:
            pages_text.append("")

    return AttachmentText(
        filename=filename,
        content_type="application/pdf",
        size=len(data),
        text="\n".join(pages_text).strip(),
        pages=len(reader.pages),
    )


def extract_docx_text(data: bytes, filename: str = "document.docx") -> AttachmentText:
    """Extract text from a DOCX byte stream using python-docx."""
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "python-docx is not installed. Install it to process DOCX files."
        ) from exc

    doc = Document(io.BytesIO(data))
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)

    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))

    text = "\n".join(paragraphs).strip()
    return AttachmentText(
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size=len(data),
        text=text,
    )


def extract_attachment_text(
    filename: str, content_type: str, data: bytes
) -> AttachmentText | None:
    """Dispatch to the correct extractor based on filename/content type.

    Returns None for unsupported file types.
    """
    lower = filename.lower()
    ctype = (content_type or "").lower()

    if lower.endswith(".pdf") or "pdf" in ctype:
        return extract_pdf_text(data, filename)
    if lower.endswith(".docx") or "wordprocessingml" in ctype:
        return extract_docx_text(data, filename)
    if lower.endswith(".doc"):
        # Legacy .doc is not supported by python-docx; report unsupported.
        return None
    if lower.endswith(".txt") or "text/plain" in ctype:
        return AttachmentText(
            filename=filename,
            content_type=content_type or "text/plain",
            size=len(data),
            text=data.decode("utf-8", errors="replace"),
        )
    return None


def combine_email_and_attachments(
    email_body: str | None,
    attachments: list[AttachmentText],
) -> str:
    """Combine email body and attachment texts into one document for extraction.

    Attachments are clearly delimited so the extraction engine can attribute
    content correctly.
    """
    parts: list[str] = []
    if email_body:
        parts.append("=== EMAIL BODY ===")
        parts.append(email_body)

    for att in attachments:
        if not att.text.strip():
            continue
        parts.append(f"=== ATTACHMENT: {att.filename} ===")
        parts.append(att.text)

    return "\n".join(parts)
