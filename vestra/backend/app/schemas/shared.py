"""
Shared response models used across all Vestra API routes.

Provides consistent JSON error shapes so every endpoint returns the same
structure for errors, making client-side error handling predictable.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all API endpoints."""
    error: str
    message: str
    path: str | None = None
    correlation_id: str | None = None
    details: Any | None = None


class SuccessResponse(BaseModel):
    """Standard success envelope for mutation endpoints."""
    success: bool = True
    message: str
    data: Any | None = None
    correlation_id: str | None = None
