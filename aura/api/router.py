"""
aura/api/router.py
------------------
Main API router aggregating all endpoints.
"""

from fastapi import APIRouter
from aura.api.endpoints import health, threads, memories

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(threads.router, tags=["Threads & Messages"])
api_router.include_router(memories.router, tags=["User Memory"])
