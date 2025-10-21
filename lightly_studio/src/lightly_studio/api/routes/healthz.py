"""This module contains the API routes for managing datasets."""

from __future__ import annotations

from fastapi import APIRouter

health_router = APIRouter()


@health_router.get("/healthz", include_in_schema=False)
def health_check() -> dict[str, str]:
    """Health check endpoint to verify the service is running."""
    return {"status": "healthy"}
