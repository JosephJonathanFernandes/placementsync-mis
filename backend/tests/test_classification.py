"""Tests for the email classification service (Module B)."""

from app.services.classification_service.classifier import (
    ClassificationResult,
    classify_email,
    is_selection_announcement,
)


def test_selection_announcement():
    result = classify_email(
        "Placement Selections - TechNova Solutions",
        "We are pleased to announce that the following students have been selected.",
    )
    assert result.category == "selection_announcement"
    assert result.confidence >= 0.8
    assert is_selection_announcement(result.category) is True


def test_shortlisting_is_not_selection():
    result = classify_email(
        "Shortlisted Candidates - Alpha Systems",
        "The following students have been shortlisted for the next round.",
    )
    assert result.category == "shortlisting_announcement"
    assert is_selection_announcement(result.category) is False


def test_shortlist_wins_over_generic_selection_word():
    # "selection" appears generically ("final selection will be announced")
    # but the email is explicitly a shortlist.
    result = classify_email(
        "Shortlisted Candidates - Alpha Systems",
        "The following students have been shortlisted. "
        "Final selection will be announced after interviews.",
    )
    assert result.category == "shortlisting_announcement"


def test_interview_notification():
    result = classify_email(
        "Interview Schedule - Beta Corp",
        "You are invited for an interview on Monday.",
    )
    assert result.category == "interview_notification"


def test_offer_letter_announcement():
    result = classify_email(
        "Offer Letter - Gamma Ltd",
        "Your offer letter has been issued.",
    )
    assert result.category == "offer_letter_announcement"


def test_unrelated_email():
    result = classify_email("Lunch menu", "The cafeteria will serve pizza today.")
    assert result.category == "unrelated"


def test_missing_content_is_safe():
    result = classify_email(None, None)
    assert result.category == "unrelated"
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result, ClassificationResult)
