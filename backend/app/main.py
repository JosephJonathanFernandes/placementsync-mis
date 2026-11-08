"""PlacementSync FastAPI application."""

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db  # noqa: F401  (ensured importable)
from app.api.routes import (
    audit,
    auth,
    backup,
    emails,
    excel,
    extraction,
    gmail,
    records,
)
from app.core.config import settings
from app.core.database import Base, create_all, get_engine
from app.core.logging import logger

app = FastAPI(
    title="PlacementSync",
    description="Intelligent Placement Email Extractor & Tracker",
    version="1.0.0-phase1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit.router)
app.include_router(auth.router)
app.include_router(backup.router)
app.include_router(emails.router)
app.include_router(extraction.router)
app.include_router(records.router)
app.include_router(excel.router)
app.include_router(gmail.router)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors gracefully."""
    logger.exception("Database error on %s %s: %s", request.method, request.url, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error. Please try again later."},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors gracefully."""
    logger.exception("Unexpected error on %s %s: %s", request.method, request.url, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )


@app.on_event("startup")
def on_startup() -> None:
    validate_settings()
    create_all()
    logger.info("PlacementSync started. Database: %s", settings.database_url)


@app.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)):
    """Health check with database connectivity verification."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.exception("Database health check failed")

    status_code = 200 if db_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if db_ok else "degraded",
            "app": settings.app_name,
            "env": settings.app_env,
            "database": "connected" if db_ok else "disconnected",
        },
    )
