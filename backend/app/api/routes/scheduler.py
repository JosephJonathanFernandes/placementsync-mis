"""Scheduler API routes (Phase 8).

Endpoints:
    GET    /api/scheduler/status       - Get scheduler status and jobs
    POST   /api/scheduler/start        - Start the scheduler
    POST   /api/scheduler/stop         - Stop the scheduler
    POST   /api/scheduler/poll         - Trigger immediate poll for current user
    GET    /api/scheduler/poll-status  - Get current user's polling config
    PUT    /api/scheduler/poll-status  - Update current user's polling config
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin, require_placement_officer, get_current_user
from app.core.database import get_db
from app.core.logging import logger
from app.models.user import User
from app.schemas.user import UserUpdate
from app.services.scheduler_service.service import get_scheduler, start_scheduler, stop_scheduler

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get(
    "/status",
    summary="Get scheduler status and all jobs (admin only)",
)
def scheduler_status(
    current_user: User = Depends(require_admin),
) -> dict:
    """Return whether the scheduler is running and all scheduled jobs."""
    scheduler = get_scheduler()
    return {
        "running": scheduler.is_running(),
        "jobs": scheduler.get_jobs(),
    }


@router.post(
    "/start",
    summary="Start the background scheduler (admin only)",
)
def start_scheduler_endpoint(
    current_user: User = Depends(require_admin),
) -> dict:
    """Start the background email polling scheduler."""
    try:
        start_scheduler()
        logger.info("Scheduler started by user %s", current_user.username)
        return {"message": "Scheduler started", "running": True}
    except Exception as exc:
        logger.exception("Failed to start scheduler")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scheduler: {exc}",
        )


@router.post(
    "/stop",
    summary="Stop the background scheduler (admin only)",
)
def stop_scheduler_endpoint(
    current_user: User = Depends(require_admin),
) -> dict:
    """Stop the background email polling scheduler."""
    try:
        stop_scheduler()
        logger.info("Scheduler stopped by user %s", current_user.username)
        return {"message": "Scheduler stopped", "running": False}
    except Exception as exc:
        logger.exception("Failed to stop scheduler")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop scheduler: {exc}",
        )


@router.post(
    "/poll",
    summary="Trigger immediate email poll for current user (placement officer only)",
)
def poll_now(
    current_user: User = Depends(require_placement_officer),
) -> dict:
    """Manually trigger email processing for the current user."""
    from app.services.gmail_service.processor import process_new_messages

    try:
        summary = process_new_messages(user_id=current_user.id, max_results=50)
        logger.info(
            "Manual poll triggered by user %s: fetched=%d stored=%d results=%d",
            current_user.username,
            summary.fetched,
            summary.stored,
            summary.created_review_results,
        )
        return {
            "message": "Poll completed",
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
    except Exception as exc:
        logger.exception("Manual poll failed for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Poll failed: {exc}",
        )


@router.get(
    "/poll-status",
    summary="Get current user's polling configuration",
)
def get_poll_status(
    current_user: CurrentUser,
) -> dict:
    """Return the current user's polling configuration."""
    return {
        "polling_enabled": current_user.polling_enabled,
        "poll_interval_minutes": current_user.poll_interval_minutes,
        "last_polled_at": current_user.last_polled_at,
    }


@router.put(
    "/poll-status",
    summary="Update current user's polling configuration",
)
def update_poll_status(
    current_user: CurrentUser,
    poll_in: UserUpdate,
    db: Session = Depends(get_db),
) -> dict:
    """Update the current user's polling configuration."""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = poll_in.model_dump(exclude_unset=True)
    if "polling_enabled" in update_data:
        user.polling_enabled = update_data["polling_enabled"]
    if "poll_interval_minutes" in update_data:
        user.poll_interval_minutes = update_data["poll_interval_minutes"]

    db.commit()
    db.refresh(user)

    # Reschedule if enabled
    scheduler = get_scheduler()
    if scheduler.is_running():
        if user.polling_enabled:
            scheduler.schedule_user(user.id, interval_minutes=user.poll_interval_minutes)
        else:
            scheduler.unschedule_user(user.id)

    logger.info(
        "Polling config updated for user %s: enabled=%s interval=%s",
        user.username,
        user.polling_enabled,
        user.poll_interval_minutes,
    )

    return {
        "polling_enabled": user.polling_enabled,
        "poll_interval_minutes": user.poll_interval_minutes,
        "last_polled_at": user.last_polled_at,
    }
