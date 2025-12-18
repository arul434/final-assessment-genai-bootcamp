#!/usr/bin/env python3
"""
Health check API routes.
"""

from fastapi import APIRouter

from src.models import HealthResponse
from src.config import settings


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.API_VERSION
    )

