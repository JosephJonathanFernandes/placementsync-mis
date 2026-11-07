"""Classify placement-related emails.

Keyword/rule-based classifier for Phase 1. It does not require any external
AI API and works offline.

Categories:
    selection_announcement - confirmed selections (enters approval workflow)
    shortlisting_announcement - shortlisted only (NOT selected students)
    interview_notification - interview call
    offer_letter_announcement - offer letter issued
    general_placement - placement-related but not a specific announcement
    unrelated - not placement related

Only ``selection_announcement`` records proceed to the human review workflow.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    category: str
    confidence: float  # 0.0 - 1.0
    matched_keywords: list[str]


# Strong signals that a selection has been confirmed.
# "offer letter" is intentionally NOT here: offer letters are their own
# category (offer_letter_announcement, status "Offered").
STRONG_SELECTION_KEYWORDS = [
    r"\bcongratulations\b",
    r"\bhas been selected\b",
    r"\bhave been selected\b",
    r"\bselected (?:students|candidates)\b",
    r"\bfinally selected\b",
    r"\bplacement offer\b",
]

# Generic placement words that alone do not confirm a selection.
SELECTION_KEYWORDS = [
    r"\bselected\b",
    r"\bselections\b",
    r"\bplaced\b",
    r"\bplacement\b",
]

# Shortlisting only - candidates are NOT selected.
SHORTLIST_KEYWORDS = [
    r"\bshortlist\b",
    r"\bshortlisted\b",
    r"\bshortlist\w*\b",
]

INTERVIEW_KEYWORDS = [
    r"\binterview\b",
    r"\binterviews\b",
    r"\binvited for interview\b",
    r"\bdrive\b",
]

GENERAL_PLACEMENT_KEYWORDS = [
    r"\bplacement\b",
    r"\bcampus\b",
]


def _contains_any(text: str, patterns: list[str]) -> list[str]:
    matched = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matched.append(pattern)
    return matched


def classify_email(subject: str | None, body_text: str | None) -> ClassificationResult:
    """Classify an email into a placement category.

    Rules are conservative: shortlisted candidates are never treated as
    selected students.
    """
    combined = " ".join([subject or "", body_text or ""])
    combined_lower = combined.lower()

    # Shortlist check first - explicitly NOT a selection.
    shortlist_matches = _contains_any(combined_lower, SHORTLIST_KEYWORDS)
    strong_selection_matches = _contains_any(combined_lower, STRONG_SELECTION_KEYWORDS)
    selection_matches = _contains_any(combined_lower, SELECTION_KEYWORDS)
    interview_matches = _contains_any(combined_lower, INTERVIEW_KEYWORDS)
    general_matches = _contains_any(combined_lower, GENERAL_PLACEMENT_KEYWORDS)

    if shortlist_matches and not strong_selection_matches:
        return ClassificationResult(
            category="shortlisting_announcement",
            confidence=0.85,
            matched_keywords=shortlist_matches,
        )

    if strong_selection_matches or selection_matches:
        confidence = 0.9 if strong_selection_matches else 0.8
        return ClassificationResult(
            category="selection_announcement",
            confidence=confidence,
            matched_keywords=(strong_selection_matches or selection_matches),
        )

    if "offer letter" in combined_lower or re.search(r"\boffer\b", combined_lower):
        return ClassificationResult(
            category="offer_letter_announcement",
            confidence=0.75,
            matched_keywords=["offer"],
        )

    if interview_matches:
        return ClassificationResult(
            category="interview_notification",
            confidence=0.8,
            matched_keywords=interview_matches,
        )

    if general_matches:
        return ClassificationResult(
            category="general_placement",
            confidence=0.5,
            matched_keywords=general_matches,
        )

    return ClassificationResult(
        category="unrelated",
        confidence=0.3,
        matched_keywords=[],
    )


def is_selection_announcement(category: str) -> bool:
    return category == "selection_announcement"
