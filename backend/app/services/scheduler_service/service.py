"""Background email polling scheduler (Phase 8).

Uses APScheduler to periodically poll connected Gmail accounts for new
placement-related emails and run them through the extraction pipeline.

The scheduler runs as a background thread within the FastAPI process.
Each user's Gmail account is polled independently at the configured interval.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job
from sqlalchemy.orm import Session

from app.core.database import get_session_factory
from app.core.logging import logger
from app.models.user import User
from app.services.gmail_service.processor import process_new_messages


class SchedulerService:
    """Manages background email polling for all users."""

    def __init__(self) -> None:
        self._scheduler: BackgroundScheduler | None = None
        self._lock = threading.Lock()
        self._jobs: dict[int, Job] = {}  # user_id -> Job

    def start(self) -> None:
        """Start the background scheduler."""
        if self._scheduler is not None and self._scheduler.running:
            return
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()
        logger.info("Email polling scheduler started")

    def stop(self) -> None:
        """Stop the background scheduler."""
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            self._jobs.clear()
            logger.info("Email polling scheduler stopped")

    def is_running(self) -> bool:
        return self._scheduler is not None and self._scheduler.running

    def _job_func(self, user_id: int) -> None:
        """Job function that processes new Gmail messages for a user."""
        from app.core.database import get_session_factory

        db = get_session_factory()()
        try:
            logger.info("Scheduled Gmail polling started for user %s", user_id)
            summary = process_new_messages(user_id=user_id, max_results=50)
            logger.info(
                "Scheduled Gmail polling completed for user %s: fetched=%d stored=%d results=%d errors=%d",
                user_id,
                summary.fetched,
                summary.stored,
                summary.created_review_results,
                summary.errors,
            )
        except Exception:
            logger.exception("Scheduled Gmail polling failed for user %s", user_id)
        finally:
            db.close()

    def schedule_user(self, user_id: int, interval_minutes: int = 15) -> None:
        """Schedule polling for a specific user.

        If the user already has a job, it is rescheduled.
        """
        if self._scheduler is None:
            self.start()

        with self._lock:
            # Remove existing job if present
            if user_id in self._jobs:
                try:
                    self._scheduler.remove_job(self._jobs[user_id].id)
                except Exception:
                    pass
                del self._jobs[user_id]

            job = self._scheduler.add_job(
                self._job_func,
                trigger=IntervalTrigger(minutes=interval_minutes),
                args=[user_id],
                id=f"gmail_poll_user_{user_id}",
                name=f"Gmail polling for user {user_id}",
                replace_existing=True,
                next_run_time=datetime.now(timezone.utc),
            )
            self._jobs[user_id] = job
            logger.info(
                "Scheduled Gmail polling for user %s every %d minutes",
                user_id,
                interval_minutes,
            )

    def unschedule_user(self, user_id: int) -> None:
        """Remove polling schedule for a specific user."""
        with self._lock:
            if user_id in self._jobs:
                try:
                    self._scheduler.remove_job(self._jobs[user_id].id)
                except Exception:
                    pass
                del self._jobs[user_id]
                logger.info("Unscheduled Gmail polling for user %s", user_id)

    def get_jobs(self) -> list[dict[str, Any]]:
        """Return information about all scheduled jobs."""
        if self._scheduler is None:
            return []
        jobs: list[dict[str, Any]] = []
        for job in self._scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat()
                    if job.next_run_time
                    else None,
                    "user_id": int(job.id.split("_")[-1])
                    if job.id.startswith("gmail_poll_user_")
                    else None,
                }
            )
        return jobs


# Global scheduler instance
scheduler = SchedulerService()


def start_scheduler() -> None:
    """Start the global scheduler and schedule all users with enabled polling."""
    scheduler.start()
    from app.core.database import get_session_factory

    db = get_session_factory()()
    try:
        users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
        for user in users:
            # Default interval: 15 minutes
            scheduler.schedule_user(user.id, interval_minutes=15)
    finally:
        db.close()


def stop_scheduler() -> None:
    """Stop the global scheduler."""
    scheduler.stop()


def get_scheduler() -> SchedulerService:
    """Get the global scheduler instance."""
    return scheduler
