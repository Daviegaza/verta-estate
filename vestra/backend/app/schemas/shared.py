"""
Shared response models used across all Vestra API routes.

Provides consistent JSON error shapes so every endpoint returns the same
structure for errors, making client-side error handling predictable.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all API endpoints."""
    error: str
    message: str
    path: Optional[str] = None
    correlation_id: Optional[str] = None
    details: Optional[Any] = None


class SuccessResponse(BaseModel):
    """Standard success envelope for mutation endpoints."""
    success: bool = True
    message: str
    data: Optional[Any] = None
    correlation_id: Optional[str] = None
