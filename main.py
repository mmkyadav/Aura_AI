"""
main.py
-------
FastAPI entry point for Aura AI Companion Backend.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from aura.config import settings
from aura.db import init_db, close_db
from aura.api.router import api_router

# Configure Logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aura")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initializes DB connection pool & schemas on startup."""
    logger.info("Starting %s...", settings.APP_NAME)
    try:
        await init_db()
    except Exception as e:
        logger.warning("Could not connect to PostgreSQL on startup (%s). Running in standalone memory mode.", e)

    yield

    logger.info("Shutting down %s...", settings.APP_NAME)
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    description="A modern, context-aware AI assistant backend built with FastAPI, LangGraph, and PostgreSQL pgvector.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API router
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "docs_url": "/docs",
        "api_v1": "/api/v1/health",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
