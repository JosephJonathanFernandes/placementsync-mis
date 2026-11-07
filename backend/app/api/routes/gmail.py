"""Gmail message fetching and automatic processing routes (Phase 2).

Endpoints:
    GET  /api/gmail/messages    - list messages matching a search query
    GET  /api/gmail/labels      - list Gmail labels
    POST /api/gmail/process     - fetch and process new messages through extraction
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.core.logging import logger
from app.services.gmail_service.client import (
    build_service,
    connection_status,
    list_labels,
    list_messages,
    load_credentials,
)
from app.services.gmail_service.processor import ProcessSummary, process_new_messages

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.get(
    "/messages",
    summary="List Gmail messages matching a placement-related search query",
)
def list_gmail_messages(
    query: str = Query(
        default='selected OR congratulations OR placement OR "offer letter" OR joining OR shortlisted',
        description="Gmail search query",
    ),
    max_results: int = Query(default=50, ge=1, le=100),
    label_ids: str | None = Query(
        default=None, description="Comma-separated Gmail label IDs to filter by"
    ),
):
    creds = load_credentials()
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Gmail account connected. Connect via /api/auth/gmail/authorize.",
        )

    service = build_service(creds)
    label_list = [l.strip() for l in label_ids.split(",")] if label_ids else None

    summaries = list_messages(
        service, query=query, max_results=max_results, label_ids=label_list
    )
    return {
        "query": query,
        "count": len(summaries),
        "messages": [
            {"id": m.id, "thread_id": m.thread_id, "snippet": m.snippet}
            for m in summaries
        ],
    }


@router.get(
    "/labels",
    summary="List Gmail labels for the connected account",
)
def get_gmail_labels():
    creds = load_credentials()
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Gmail account connected.",
        )
    service = build_service(creds)
    labels = list_labels(service)
    return {"labels": labels}


@router.post(
    "/process",
    summary="Fetch new Gmail messages and run them through the extraction pipeline",
)
def process_gmail_messages(
    query: str = Query(
        default='selected OR congratulations OR placement OR "offer letter" OR joining OR shortlisted',
        description="Gmail search query for new messages",
    ),
    max_results: int = Query(default=50, ge=1, le=100),
    label_ids: str | None = Query(
        default=None, description="Comma-separated Gmail label IDs to filter by"
    ),
):
    creds = load_credentials()
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Gmail account connected.",
        )

    label_list = [l.strip() for l in label_ids.split(",")] if label_ids else None

    try:
        summary: ProcessSummary = process_new_messages(
            query=query, max_results=max_results, label_ids=label_list
        )
    except Exception:
        logger.exception("Gmail automatic processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Gmail messages",
        )

    return {
        "message": "Gmail processing complete",
        "summary": {
            "fetched": summary.fetched,
            "stored": summary.stored,
            "skipped_duplicate": summary.skipped_duplicate,
            "classified_selection": summary.classified_selection,
            "created_review_results": summary.created_review_results,
            "attachment_errors": summary.attachment_errors,
            "errors": summary.errors,
        },
    }
