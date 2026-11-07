"""PlacementSync FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_db  # noqa: F401  (ensured importable)
from app.api.routes import auth, emails, excel, extraction, gmail, records
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

app.include_router(auth.router)
app.include_router(emails.router)
app.include_router(extraction.router)
app.include_router(records.router)
app.include_router(excel.router)
app.include_router(gmail.router)


@app.on_event("startup")
def on_startup() -> None:
    create_all()
    logger.info("PlacementSync started. Database: %s", settings.database_url)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
