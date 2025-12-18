#!/usr/bin/env python3
"""
Health check API routes.
"""

from fastapi import APIRouter

from models import HealthResponse
from config import settings


router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        version=settings.API_VERSION
    )


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.API_VERSION
    )

