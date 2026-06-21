"""
Shared Pydantic schemas used across all Vestra API routes.

VESTRA v4.3.0 — Extended with pagination, sorting, geo, currency, and date-range models.
Provides consistent request/response shapes so every endpoint returns the same
structure for errors, paginated lists, and success responses.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ── Envelope Types ────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error envelope returned by all API endpoints."""
    error: str
    message: str
    path: str | None = None
    correlation_id: str | None = None
    details: Any | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(BaseModel):
    """Standard success envelope for mutation endpoints."""
    success: bool = True
    message: str
    data: Any | None = None
    correlation_id: str | None = None


class HealthResponse(BaseModel):
    """Detailed health check response."""
    status: str = "healthy"
    version: str = "4.3.0"
    uptime_seconds: float = 0.0
    checks: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Pagination ─────────────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    """Pagination metadata."""
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items across all pages")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse[T](BaseModel):
    """Generic paginated response wrapper."""
    items: list[T] = Field(default_factory=list, description="List of items for the current page")
    pagination: PaginationMeta
    filters_applied: dict[str, Any] | None = Field(None, description="Active filters on the query")


class PageParams(BaseModel):
    """Common pagination query parameters."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")

    @field_validator("page_size")
    @classmethod
    def clamp_page_size(cls, v: int) -> int:
        return max(1, min(v, 100))


class SortParams(BaseModel):
    """Common sort query parameters."""
    sort_by: str | None = Field(None, description="Field to sort by")
    sort_order: str = Field("asc", pattern=r"^(asc|desc)$", description="Sort direction")

    @field_validator("sort_order")
    @classmethod
    def normalize_order(cls, v: str) -> str:
        return v.lower().strip() if v.lower().strip() in ("asc", "desc") else "asc"


# ── Geo / Location ─────────────────────────────────────────────────────────

class GeoPoint(BaseModel):
    """Geographic point."""
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class BoundingBox(BaseModel):
    """Geographic bounding box for map searches."""
    north: float = Field(..., ge=-90, le=90)
    south: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)
    west: float = Field(..., ge=-180, le=180)


class AddressSuggestion(BaseModel):
    """Address autocomplete suggestion."""
    formatted: str
    lat: float
    lng: float
    city: str | None = None
    county: str | None = None


# ── Currency ───────────────────────────────────────────────────────────────

class CurrencyInfo(BaseModel):
    """Currency metadata."""
    code: str
    symbol: str
    name: str
    rate_to_kes: float
    updated_at: datetime


# ── Date Range ─────────────────────────────────────────────────────────────

class DateRange(BaseModel):
    """Date range filter."""
    start: datetime | None = Field(None, description="Start date (inclusive)")
    end: datetime | None = Field(None, description="End date (inclusive)")

    @field_validator("end")
    @classmethod
    def end_must_be_after_start(cls, v: datetime | None, info: Any) -> datetime | None:
        start = info.data.get("start")
        if v and start and v < start:
            raise ValueError("end date must be after start date")
        return v
