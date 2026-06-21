from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.property import ListingType, PropertyStatus, PropertyType


class PropertyCreate(BaseModel):
    title: str
    description: str | None = None
    property_type: PropertyType
    listing_type: ListingType
    address: str
    city: str
    county: str
    country: str = "Kenya"
    latitude: float | None = None
    longitude: float | None = None
    price: float
    currency: str = "KES"
    price_negotiable: bool = False
    bedrooms: int | None = None
    bathrooms: int | None = None
    size_sqft: float | None = None
    year_built: int | None = None
    amenities: list[str] = []
    images: list[str] = []

    @field_validator("price")
    @classmethod
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v


class PropertyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    address: str | None = None
    city: str | None = None
    county: str | None = None
    price: float | None = None
    price_negotiable: bool | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    size_sqft: float | None = None
    amenities: list[str] | None = None
    images: list[str] | None = None
    status: PropertyStatus | None = None


class PropertyResponse(BaseModel):
    id: int
    owner_id: int
    title: str
    description: str | None
    property_type: PropertyType
    listing_type: ListingType
    status: PropertyStatus
    address: str
    city: str
    county: str
    country: str
    latitude: float | None
    longitude: float | None
    price: float
    currency: str
    price_negotiable: bool
    bedrooms: int | None
    bathrooms: int | None
    size_sqft: float | None
    amenities: list[str]
    images: list[str]
    trust_score: float | None
    is_verified: bool
    verification_badge: str | None
    views: int
    inquiries: int
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class PropertyListResponse(BaseModel):
    items: list[PropertyResponse]
    total: int
    page: int
    pages: int
    size: int


class PropertySearch(BaseModel):
    query: str | None = None
    city: str | None = None
    county: str | None = None
    property_type: PropertyType | None = None
    listing_type: ListingType | None = None
    min_price: float | None = None
    max_price: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    min_size: float | None = None
    max_size: float | None = None
    verified_only: bool = False
    page: int = 1
    size: int = 20
