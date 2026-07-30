"""
Health-check router.

Returns application liveness and readiness probes.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health-check response schema."""

    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health_check() -> HealthResponse:
    """Return service health status."""
    from app.config import settings

    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
    )


@router.get("/ready", response_model=HealthResponse, summary="Readiness probe")
async def readiness_check() -> HealthResponse:
    """Return service readiness status."""
    from app.config import settings

    return HealthResponse(
        status="ready",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
    )
