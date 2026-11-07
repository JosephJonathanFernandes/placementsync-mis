"""Parse .eml files and raw email messages into a normalized structure.

Uses only the standard library ``email`` module plus BeautifulSoup for HTML
to plain-text conversion. No network access is performed here.
"""

from email import policy
from email.parser import BytesParser
from email.header import decode_header, make_header
from typing import Any

from bs4 import BeautifulSoup


class ParsedEmail:
    """Normalized representation of an email message."""

    def __init__(
        self,
        *,
        message_id: str,
        subject: str | None,
        sender: str | None,
        date: str | None,
        body_text: str | None,
        body_html: str | None,
        attachments: list[dict[str, Any]],
    ) -> None:
        self.message_id = message_id
        self.subject = subject
        self.sender = sender
        self.date = date
        self.body_text = body_text
        self.body_html = body_html
        self.attachments = attachments


def _decode_header_value(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _get_best_text_body(msg) -> tuple[str | None, str | None]:
    """Return (plain_text, html) body parts from an email message."""
    plain: str | None = None
    html: str | None = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                continue
            try:
                payload = part.get_content(charset="utf-8", errors="replace")
            except Exception:
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8", errors="replace")
            if content_type == "text/plain" and plain is None:
                plain = payload
            elif content_type == "text/html" and html is None:
                html = payload
    else:
        content_type = msg.get_content_type()
        try:
            payload = msg.get_content(charset="utf-8", errors="replace")
        except Exception:
            payload = msg.get_payload(decode=True)
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", errors="replace")
        if content_type == "text/html" or _looks_like_html(payload):
            html = payload
        else:
            plain = payload

    return plain, html


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Remove script and style elements
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    # Collapse excessive blank lines
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned


def _looks_like_html(text: str | None) -> bool:
    if not text:
        return False
    stripped = text.lstrip()
    return stripped.startswith("<") and any(
        token in stripped[:200].lower() for token in ["<html", "<body", "<p>", "<table", "<div"]
    )


def parse_eml_bytes(data: bytes) -> ParsedEmail:
    """Parse raw .eml bytes into a ParsedEmail."""
    msg = BytesParser(policy=policy.default).parsebytes(data)

    message_id = msg.get("Message-ID") or msg.get("Message-Id") or ""
    subject = _decode_header_value(msg.get("Subject"))
    sender = _decode_header_value(msg.get("From")) or msg.get("From")
    date = msg.get("Date")

    body_text, body_html = _get_best_text_body(msg)

    # If only HTML exists, derive a plain-text version from it.
    if body_text is None and body_html is not None:
        body_text = _html_to_text(body_html)

    attachments: list[dict[str, Any]] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                filename = part.get_filename()
                if filename:
                    filename = _decode_header_value(filename) or filename
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True) or b""
                attachments.append(
                    {
                        "filename": filename,
                        "content_type": content_type,
                        "size": len(payload),
                    }
                )

    return ParsedEmail(
        message_id=message_id,
        subject=subject,
        sender=sender,
        date=date,
        body_text=body_text,
        body_html=body_html,
        attachments=attachments,
    )


def parse_eml_file(path: str) -> ParsedEmail:
    """Parse an .eml file from disk."""
    with open(path, "rb") as fh:
        return parse_eml_bytes(fh.read())
