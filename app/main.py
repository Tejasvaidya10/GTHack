"""MedSift AI — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.database import init_db
from api.routes import transcribe, analyze, visits, export, trials, literature, feedback, analytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info("Initializing MedSift AI...")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("MedSift AI shutting down")


app = FastAPI(
    title="MedSift AI",
    description="AI-powered healthcare conversation intelligence system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for hackathon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route modules
app.include_router(transcribe.router, tags=["Transcription"])
app.include_router(analyze.router, tags=["Analysis"])
app.include_router(visits.router, tags=["Visits"])
app.include_router(export.router, tags=["Export"])
app.include_router(trials.router, tags=["Clinical Trials"])
app.include_router(literature.router, tags=["Literature"])
app.include_router(feedback.router, tags=["Feedback"])
app.include_router(analytics.router, tags=["Analytics"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "name": "MedSift AI",
        "status": "running",
        "version": "1.0.0",
        "tagline": "Sift through medical conversations. Surface what matters.",
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}
