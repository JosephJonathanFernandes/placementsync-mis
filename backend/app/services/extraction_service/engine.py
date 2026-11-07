"""Offline, rule-based information extraction engine for Phase 1.

Extracts placement information from email text without any external AI API.
All heuristics are deterministic and auditable. Missing fields are reported
rather than invented, and extraction warnings surface ambiguous data for
human review.

Extraction is performed line-by-line so that structured fields (Name:, Reg
No:, bullet lists, HTML-table-derived lines) do not bleed into each other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ExtractedStudent:
    name: str
    registration_number: str | None = None
    branch: str | None = None
    job_role: str | None = None
    package: str | None = None
    confidence: float = 0.0
    context_snippet: str = ""


@dataclass
class ExtractionData:
    company_name: str | None = None
    company_confidence: float = 0.0
    students: list[ExtractedStudent] = field(default_factory=list)
    job_role: str | None = None
    package: str | None = None
    selection_date: str | None = None
    status: str = "Selected"  # Selected | Shortlisted | Offered
    confidence: float = 0.0
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_name": self.company_name,
            "company_confidence": self.company_confidence,
            "students": [
                {
                    "name": s.name,
                    "registration_number": s.registration_number,
                    "branch": s.branch,
                    "job_role": s.job_role,
                    "package": s.package,
                    "confidence": s.confidence,
                    "context_snippet": s.context_snippet,
                }
                for s in self.students
            ],
            "job_role": self.job_role,
            "package": self.package,
            "selection_date": self.selection_date,
            "status": self.status,
            "confidence": self.confidence,
            "missing_fields": self.missing_fields,
            "warnings": self.warnings,
            "raw": self.raw,
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BRANCHES = [
    "CSE", "IT", "ECE", "EEE", "ME", "CE", "CIVIL", "MECH", "E&CE", "E&EE",
    "COMPUTER SCIENCE", "INFORMATION TECHNOLOGY", "ELECTRONICS",
    "ELECTRICAL", "MECHANICAL",
]

BRANCH_ALIASES = {
    "CSE": "CSE", "COMPUTER SCIENCE": "CSE", "COMPUTER SCIENCE & ENGINEERING": "CSE",
    "IT": "IT", "INFORMATION TECHNOLOGY": "IT",
    "ECE": "ECE", "ELECTRONICS AND COMMUNICATION": "ECE", "E&CE": "ECE",
    "EEE": "EEE", "ELECTRICAL AND ELECTRONICS": "EEE", "E&EE": "EEE",
    "ME": "ME", "MECHANICAL": "ME", "MECH": "ME",
    "CE": "CE", "CIVIL": "CE", "CIVIL ENGINEERING": "CE",
}

SIGNATURE_MARKERS = [
    "regards",
    "thanks & regards",
    "thank you",
    "placement cell",
    "placement office",
    "training & placement",
    "training and placement",
    "placement officer",
    "sent from my iphone",
    "sent from my android",
    "--",
]

COMPANY_SUFFIXES = [
    "private limited", "pvt ltd", "ltd", "limited", "technologies", "technology",
    "solutions", "services", "systems", "india", "inc", "corp", "corporation",
    "llp",
]

GENERIC_WORDS = {
    "Congratulations", "Congrats", "Placement", "Selection", "Selected",
    "Student", "Students", "Company", "Role", "Package", "Branch",
    "Computer", "Science", "Technology", "Information", "Electronics",
    "Electrical", "Mechanical", "Civil", "Dear", "Respected", "Sir", "Madam",
    "Team", "Office", "Cell", "Section", "Coordinator",
}

NAME_STOP_WORDS = {
    "reg no", "registration number", "roll no", "job role", "position",
    "designation", "company name", "student name", "ctc", "package", "branch",
    "selected candidates", "selected students",
}

DATE_PATTERNS = [
    r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b",
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4})\b",
]

PACKAGE_PATTERNS = [
    r"CTC\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*(?:-\s*[0-9]+(?:\.[0-9]+)?)*\s*(?:LPA|lakhs|Lakhs|L\.P\.A\.)",
    r"package\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*(?:LPA|lakhs|Lakhs)",
    r"salary\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*(?:LPA|lakhs|Lakhs)",
    r"([0-9]+(?:\.[0-9]+)?)\s*LPA",
    r"₹\s*([0-9]+(?:\.[0-9]+)?)\s*(?:LPA|lakhs)?",
    r"([0-9]+(?:\.[0-9]+)?)\s*lakhs per annum",
]

REG_PATTERNS = [
    r"reg(?:istration)?\s*(?:no|number)?\s*[:=]?\s*([A-Za-z0-9\-/]+)",
    r"roll\s*(?:no|number)?\s*[:=]?\s*([A-Za-z0-9\-/]+)",
    r"\b(\d{2}[A-Z]{2,4}\d{3,})\b",           # e.g. 22CS014, 22IT088
    r"\b([A-Za-z]{2,4}[- ]?\d{4,6}[A-Za-z]?)\b",
]

ROLE_PATTERNS = [
    r"role\s*[:=]\s*([^\n,;]+)",
    r"position\s*[:=]\s*([^\n,;]+)",
    r"designation\s*[:=]\s*([^\n,;]+)",
    r"\bas\s+a(n)?\s+([A-Z][A-Za-z\s]{2,60})",
    r"\bhired\s+as\s+([^\n,;]+)",
]

COMPANY_LINE_PATTERNS = [
    r"company\s*[:=]\s*([^\n,;]+)",
    r"hiring\s+company\s*[:=]\s*([^\n,;]+)",
    r"from\s+([A-Z][A-Za-z& .'()]{2,60}(?:private limited|pvt ltd|limited|technologies|technology|solutions|services|systems|india|inc|corp|corporation|llp))",
    r"placed\s+at\s+([A-Z][A-Za-z& .'()]{2,60})",
    r"joined\s+([A-Z][A-Za-z& .'()]{2,60})",
]

NAME_LABEL_PATTERNS = [
    r"^\s*(?:name|student\s*(?:name)?|name of the student|candidate name)\s*[:=]\s*(.+)$",
]

SELECTION_CONTEXT = [
    r"\bselected\b", r"\bselections\b", r"\bcongratulations\b", r"\bplaced\b",
    r"\bhas been selected\b", r"\bhave been selected\b", r"\boffered\b",
    r"\boffer letter\b", r"\bjoined\b",
]

NAME_TOKEN_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b")
BULLET_LINE_RE = re.compile(r"^[\s\u2022\-\*\(\)0-9\.]+\s*(.+)$")

# A single field line that belongs to the most recently seen student name.
FIELD_PATTERNS = [
    (r"reg(?:istration)?\s*(?:no|number)?\s*[:=]?\s*(.+)$", "registration_number"),
    (r"roll\s*(?:no|number)?\s*[:=]?\s*(.+)$", "registration_number"),
    (r"branch\s*[:=]?\s*(.+)$", "branch"),
    (r"job\s*role\s*[:=]?\s*(.+)$", "job_role"),
    (r"role\s*[:=]?\s*(.+)$", "job_role"),
    (r"position\s*[:=]?\s*(.+)$", "job_role"),
    (r"designation\s*[:=]?\s*(.+)$", "job_role"),
    (r"ctc\s*[:=]?\s*(.+)$", "package"),
    (r"package\s*[:=]?\s*(.+)$", "package"),
    (r"salary\s*[:=]?\s*(.+)$", "package"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _strip_signature(text: str) -> str:
    """Remove signature/disclaimer tail from email body.

    Only line-anchored markers count, so that constructs like the forwarded
    message delimiter (``---------- Forwarded Message ----------``) are not
    mistaken for a signature separator.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if not stripped:
            continue
        for marker in SIGNATURE_MARKERS:
            if stripped == marker or stripped.startswith(marker + " ") or stripped.startswith(marker + ",") or stripped.startswith(marker + ":"):
                return "\n".join(lines[:i])
    return text


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_from_text(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return _clean(match.group(1))
    return None


def _extract_branch(text: str) -> str | None:
    for pattern in BRANCHES:
        if re.search(r"\b" + re.escape(pattern) + r"\b", text, re.IGNORECASE):
            return BRANCH_ALIASES.get(pattern.upper(), pattern.upper())
    return None


def _extract_package(text: str) -> str | None:
    for pattern in PACKAGE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1)
            if "LPA" in pattern.upper() or "lakhs" in pattern.lower():
                return f"{value} LPA"
            return value
    return None


def _extract_registration(text: str) -> str | None:
    for pattern in REG_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _clean(match.group(1))
    return None


def _extract_role(text: str) -> str | None:
    for pattern in ROLE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = _truncate_at_next_field(_clean(match.group(1)))
            if value:
                return value
    return None


def _is_likely_name(token: str) -> bool:
    if not token:
        return False
    token_clean = _clean(token)
    if token_clean.lower() in NAME_STOP_WORDS:
        return False
    words = token_clean.split()
    if len(words) < 2 or len(words) > 4:
        return False
    if any(w in GENERIC_WORDS for w in words):
        return False
    if any(w.upper() in {b.upper() for b in BRANCHES} for w in words):
        return False
    return True


def _window(lines: list[str], index: int, radius: int = 2) -> str:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    return " ".join(lines[start:end])


def _truncate_at_next_field(value: str) -> str:
    """Cut a value off at the start of the next known field."""
    cut = re.split(
        r"\s+(?:CTC|Package|Salary|Name|Registration|Roll No|Branch|Job Role|Role|Position)\b",
        value,
        maxsplit=1,
        flags=re.IGNORECASE,
    )
    return _clean(cut[0])


def _parse_field_line(line: str) -> tuple[str, str] | None:
    """Return (field_key, value) if the line is a single field declaration."""
    for pattern, key in FIELD_PATTERNS:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            value = _clean(match.group(1))
            value = _truncate_at_next_field(value)
            if value:
                return key, value
    return None


# ---------------------------------------------------------------------------
# Company extraction
# ---------------------------------------------------------------------------


def _extract_company(lines: list[str], subject: str | None) -> tuple[str | None, float]:
    """Return (company_name, confidence)."""
    candidates: list[tuple[str, float]] = []

    for line in lines:
        for pattern in COMPANY_LINE_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                name = _clean(match.group(1))
                name = _truncate_at_next_field(name)
                if len(name) >= 2 and not any(
                    w in GENERIC_WORDS for w in name.split()
                ):
                    conf = 0.9 if pattern.startswith(r"company") else 0.75
                    candidates.append((name, conf))

    # Subject line fallback
    if subject:
        subj = subject.strip()
        for sep in ["-", "–", ":", "|"]:
            if sep in subj:
                parts = [p.strip() for p in subj.split(sep)]
                for part in parts:
                    plower = part.lower()
                    if any(s in plower for s in COMPANY_SUFFIXES) or re.search(
                        r"\b[A-Z][a-z]+\s+(?:Technologies|Solutions|Ltd|Limited)\b",
                        part,
                    ):
                        if len(part) >= 3:
                            candidates.append((part, 0.6))
                break

    if not candidates:
        return None, 0.0

    candidates.sort(key=lambda x: (x[1], len(x[0])), reverse=True)
    return candidates[0]


# ---------------------------------------------------------------------------
# HTML table extraction
# ---------------------------------------------------------------------------


def _extract_from_html_tables(html: str | None) -> list[dict[str, str]]:
    """Extract student-like rows from HTML tables.

    When a header row is present, cells are mapped to named fields
    (name, registration_number, branch, job_role, package); otherwise the
    raw row text is returned for token-based fallback extraction.
    """
    rows: list[dict[str, str]] = []
    if not html:
        return rows
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if not trs:
            continue
        header_index: int | None = None
        column_map: dict[str, int] = {}
        for idx, tr in enumerate(trs):
            cells = [c.get_text(" ", strip=True).lower() for c in tr.find_all(["td", "th"])]
            if not cells:
                continue
            if any(
                key in cells
                for key in [
                    "student name",
                    "name",
                    "reg no",
                    "registration no",
                    "branch",
                    "role",
                    "ctc",
                    "package",
                ]
            ):
                header_index = idx
                for pos, cell in enumerate(cells):
                    if "student name" in cell or cell == "name":
                        column_map["name"] = pos
                    elif "reg" in cell or "roll" in cell:
                        column_map["registration_number"] = pos
                    elif "branch" in cell:
                        column_map["branch"] = pos
                    elif "role" in cell:
                        column_map["job_role"] = pos
                    elif "ctc" in cell or "package" in cell:
                        column_map["package"] = pos
                break

        for idx, tr in enumerate(trs):
            if header_index is not None and idx <= header_index:
                continue
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if not cells:
                continue
            joined = " | ".join(cells)
            if column_map and "name" in column_map:
                mapped: dict[str, str] = {"raw": joined, "cells": cells}
                for key, pos in column_map.items():
                    if pos < len(cells):
                        mapped[key] = cells[pos]
                if mapped.get("name") and _is_likely_name(mapped["name"]):
                    rows.append(mapped)
            else:
                if NAME_TOKEN_RE.search(joined) and (
                    re.search(r"\b(?:reg|roll)\b", joined, re.IGNORECASE)
                    or _extract_branch(joined)
                ):
                    rows.append({"raw": joined, "cells": cells})
    return rows


# ---------------------------------------------------------------------------
# Student extraction (line-aware)
# ---------------------------------------------------------------------------


def _extract_students_from_labeled_blocks(
    lines: list[str],
) -> list[ExtractedStudent]:
    """Stateful scan: a 'Name:' line opens a student record; subsequent
    field lines (Reg No, Branch, Role, CTC...) belong to it until the next
    name line. This mirrors how placement emails are actually written."""
    students: list[ExtractedStudent] = []
    current: dict[str, str | None] | None = None

    def flush() -> None:
        nonlocal current
        if current and current.get("name") and _is_likely_name(current["name"]):  # type: ignore[arg-type]
            students.append(
                ExtractedStudent(
                    name=str(current["name"]),  # type: ignore[arg-type]
                    registration_number=current.get("registration_number"),
                    branch=current.get("branch"),
                    job_role=current.get("job_role"),
                    package=current.get("package"),
                    confidence=0.85,
                    context_snippet=str(current["name"]),  # type: ignore[arg-type]
                )
            )
        current = None

    for line in lines:
        name_match = re.match(NAME_LABEL_PATTERNS[0], line, re.IGNORECASE)
        if name_match:
            flush()
            name = _clean(name_match.group(1))
            name = name.rstrip(":;,-").strip()
            current = {
                "name": name,
                "registration_number": None,
                "branch": None,
                "job_role": None,
                "package": None,
            }
            continue
        if current is not None:
            parsed = _parse_field_line(line)
            if parsed:
                key, value = parsed
                current[key] = value
                continue
            # A line that looks like a new entry (bullet, or all-caps label)
            # ends the current block.
            if BULLET_LINE_RE.match(line) or re.match(r"^[A-Z][A-Za-z ]{2,40}:", line):
                flush()
    flush()
    return students


def _extract_students_from_selection_list(lines: list[str]) -> list[ExtractedStudent]:
    """'The following students have been selected: A, B, C' style lines."""
    students: list[ExtractedStudent] = []
    for index, line in enumerate(lines):
        for pattern in SELECTION_CONTEXT:
            match = re.search(pattern, line, re.IGNORECASE)
            if not match:
                continue
            after = line[match.end():]
            colon_idx = after.find(":")
            if colon_idx == -1:
                continue
            list_part = after[colon_idx + 1:]
            for chunk in re.split(r"[,;]|(?:\band\b)", list_part):
                chunk = _clean(chunk)
                chunk = re.sub(r"^(?:Mr\.?|Ms\.?|Mrs\.?)\s+", "", chunk)
                if _is_likely_name(chunk):
                    students.append(
                        ExtractedStudent(
                            name=chunk,
                            confidence=0.7,
                            context_snippet=line,
                        )
                    )
    return students


def _extract_students_from_bullet_lines(lines: list[str]) -> list[ExtractedStudent]:
    """Bullet / numbered lines such as '• Name (Reg No: ..., Branch) - Role: ...'."""
    students: list[ExtractedStudent] = []
    for index, line in enumerate(lines):
        if not BULLET_LINE_RE.match(line):
            continue
        # Skip email-forwarding delimiters such as "---------- Forwarded Message ----------"
        if re.match(r"^\s*[-=_]{3,}", line) and re.search(
            r"forwarded|original message", line, re.IGNORECASE
        ):
            continue
        cleaned = BULLET_LINE_RE.match(line).group(1)  # type: ignore[union-attr]
        # Name is the leading capitalized phrase up to a separator
        name_part = re.split(
            r"\s*[\(,-]\s*|\s+-\s+|\bRole\b|\bPackage\b|\bCTC\b", cleaned, maxsplit=1
        )[0]
        name = _clean(name_part)
        name = re.sub(r"^(?:Mr\.?|Ms\.?|Mrs\.?)\s+", "", name)
        if not _is_likely_name(name):
            continue
        window = _window(lines, index)
        students.append(
            ExtractedStudent(
                name=name,
                registration_number=_extract_registration(line)
                or _extract_registration(window),
                branch=_extract_branch(line) or _extract_branch(window),
                job_role=_extract_role(line) or _extract_role(window),
                package=_extract_package(line) or _extract_package(window),
                confidence=0.8,
                context_snippet=line,
            )
        )
    return students


def _looks_like_student_entry(line: str) -> bool:
    """A line that is likely a list entry for a student (has a reg number,
    branch, or is a short standalone name)."""
    if _extract_registration(line) or _extract_branch(line):
        return True
    if re.fullmatch(r"\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\s*", line or ""):
        return True
    return False


def _extract_students_from_tokens(lines: list[str]) -> list[ExtractedStudent]:
    """Fallback: capitalized name tokens in selection-context list lines.

    Sentence-style announcements (e.g. "X has selected the following students")
    and lines without any structural student signal are skipped to avoid
    picking up company names or role titles as student names.
    """
    students: list[ExtractedStudent] = []
    seen: set[str] = set()
    for index, line in enumerate(lines):
        if not re.search("|".join(SELECTION_CONTEXT), line, re.IGNORECASE):
            continue
        if re.search(r"\b(has been selected|have been selected|has selected|congratulates)\b", line, re.IGNORECASE):
            continue
        if not _looks_like_student_entry(line):
            continue
        for match in NAME_TOKEN_RE.finditer(line):
            token = _clean(match.group(0))
            if token in seen:
                continue
            if not _is_likely_name(token):
                continue
            seen.add(token)
            students.append(
                ExtractedStudent(
                    name=token,
                    registration_number=_extract_registration(line),
                    branch=_extract_branch(line),
                    confidence=0.55,
                    context_snippet=line,
                )
            )
    return students


def _dedupe_students(students: list[ExtractedStudent]) -> list[ExtractedStudent]:
    merged: dict[str, ExtractedStudent] = {}
    for s in students:
        key = s.name.lower()
        if key in merged:
            existing = merged[key]
            if not existing.registration_number and s.registration_number:
                existing.registration_number = s.registration_number
            if not existing.branch and s.branch:
                existing.branch = s.branch
            if not existing.job_role and s.job_role:
                existing.job_role = s.job_role
            if not existing.package and s.package:
                existing.package = s.package
            existing.confidence = max(existing.confidence, s.confidence)
        else:
            merged[key] = s
    return list(merged.values())


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------


class ExtractionEngine:
    """Deterministic extraction engine for placement emails."""

    def __init__(self) -> None:
        self.name = "rule-based-engine-v2"

    def extract(
        self,
        *,
        subject: str | None,
        body_text: str | None,
        body_html: str | None,
        email_date: str | None = None,
        classification_category: str | None = None,
    ) -> ExtractionData:
        data = ExtractionData()

        text = body_text or ""
        html_text = _html_to_text(body_html) if body_html else ""

        combined = _strip_signature(text)
        if html_text and not text.strip():
            combined = html_text
        elif html_text:
            combined = combined + "\n" + html_text

        lines = [line.strip() for line in combined.splitlines() if line.strip()]
        joined = " ".join(lines)

        # --- Company ---
        company, conf = _extract_company(lines, subject)
        data.company_name = company
        data.company_confidence = conf

        # --- Students ---
        students: list[ExtractedStudent] = []
        students += _extract_students_from_labeled_blocks(lines)
        students += _extract_students_from_selection_list(lines)
        students += _extract_students_from_bullet_lines(lines)
        students += _extract_students_from_tokens(lines)

        # HTML table rows
        for row in _extract_from_html_tables(body_html):
            if "name" in row and _is_likely_name(row.get("name", "")):
                students.append(
                    ExtractedStudent(
                        name=row["name"],
                        registration_number=row.get("registration_number"),
                        branch=row.get("branch"),
                        job_role=row.get("job_role"),
                        package=row.get("package"),
                        confidence=0.85,
                        context_snippet="HTML table row",
                    )
                )
                continue
            raw = row["raw"]
            name_match = NAME_TOKEN_RE.search(raw)
            if name_match and _is_likely_name(name_match.group(0)):
                students.append(
                    ExtractedStudent(
                        name=name_match.group(0),
                        registration_number=_extract_registration(raw),
                        branch=_extract_branch(raw),
                        confidence=0.8,
                        context_snippet="HTML table row",
                    )
                )

        students = _dedupe_students(students)
        data.students = students

        for s in students:
            if s.confidence < 0.6 and s.name:
                data.warnings.append(
                    f"Student '{s.name}' detected with low confidence; verify against the original email."
                )

        # --- Role / Package / Date (document-level fallback) ---
        if not any(s.job_role for s in students):
            data.job_role = _extract_role(joined)
        if not any(s.package for s in students):
            data.package = _extract_package(joined)
        for pattern in DATE_PATTERNS:
            match = re.search(pattern, joined)
            if match:
                data.selection_date = match.group(1)
                break
        if not data.selection_date and email_date:
            data.selection_date = email_date

        # Document-level role/package fallback from the first student that has them
        if not data.job_role:
            for s in students:
                if s.job_role:
                    data.job_role = s.job_role
                    break
        if not data.package:
            for s in students:
                if s.package:
                    data.package = s.package
                    break

        # Per-student fallback: inherit document-level role/package if missing
        for s in students:
            if not s.job_role and data.job_role:
                s.job_role = data.job_role
            if not s.package and data.package:
                s.package = data.package

        if classification_category:
            if classification_category == "shortlisting_announcement":
                data.status = "Shortlisted"
            elif classification_category == "offer_letter_announcement":
                data.status = "Offered"
            else:
                data.status = "Selected"

        # --- Confidence & missing fields ---
        conf_parts: list[float] = []
        if data.company_name:
            conf_parts.append(data.company_confidence)
        if data.students:
            conf_parts.append(
                sum(s.confidence for s in data.students) / len(data.students)
            )
        if data.package:
            conf_parts.append(0.8)
        data.confidence = (
            round(sum(conf_parts) / len(conf_parts), 2) if conf_parts else 0.2
        )

        if not data.company_name:
            data.missing_fields.append("company_name")
            data.warnings.append(
                "Company name could not be determined from the email."
            )
        if not data.students:
            data.missing_fields.append("students")
            data.warnings.append(
                "No student names were extracted. The email may not contain a "
                "selection list."
            )
        if not data.job_role:
            data.missing_fields.append("job_role")
        if not data.package:
            data.missing_fields.append("package")
            data.warnings.append("CTC/package not found in the email.")
        if not data.selection_date:
            data.missing_fields.append("selection_date")

        if not data.students and data.confidence > 0.4:
            data.warnings.append(
                "Email looks placement-related but no structured student data "
                "was found."
            )

        data.raw = {
            "subject": subject,
            "body_preview": joined[:500],
            "table_rows": _extract_from_html_tables(body_html),
        }
        return data

    def extract_from_parsed_email(
        self,
        *,
        parsed_email,
        email_date: str | None = None,
        classification_category: str | None = None,
    ) -> ExtractionData:
        return self.extract(
            subject=parsed_email.subject,
            body_text=parsed_email.body_text,
            body_html=parsed_email.body_html,
            email_date=email_date,
            classification_category=classification_category,
        )
