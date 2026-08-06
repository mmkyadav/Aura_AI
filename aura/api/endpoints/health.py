"""
aura/api/endpoints/health.py
-----------------------------
Healthcheck endpoint.
"""

from fastapi import APIRouter
from aura.config import settings
from aura.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        app=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
    )
