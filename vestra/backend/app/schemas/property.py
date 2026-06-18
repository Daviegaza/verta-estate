from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.property import PropertyType, ListingType, PropertyStatus


class PropertyCreate(BaseModel):
    title: str
    description: Optional[str] = None
    property_type: PropertyType
    listing_type: ListingType
    address: str
    city: str
    county: str
    country: str = "Kenya"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price: float
    currency: str = "KES"
    price_negotiable: bool = False
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    size_sqft: Optional[float] = None
    year_built: Optional[int] = None
    amenities: List[str] = []
    images: List[str] = []

    @field_validator("price")
    @classmethod
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v


class PropertyUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    price: Optional[float] = None
    price_negotiable: Optional[bool] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    size_sqft: Optional[float] = None
    amenities: Optional[List[str]] = None
    images: Optional[List[str]] = None
    status: Optional[PropertyStatus] = None


class PropertyResponse(BaseModel):
    id: int
    owner_id: int
    title: str
    description: Optional[str]
    property_type: PropertyType
    listing_type: ListingType
    status: PropertyStatus
    address: str
    city: str
    county: str
    country: str
    latitude: Optional[float]
    longitude: Optional[float]
    price: float
    currency: str
    price_negotiable: bool
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    size_sqft: Optional[float]
    amenities: List[str]
    images: List[str]
    trust_score: Optional[float]
    is_verified: bool
    verification_badge: Optional[str]
    views: int
    inquiries: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PropertyListResponse(BaseModel):
    items: List[PropertyResponse]
    total: int
    page: int
    pages: int
    size: int


class PropertySearch(BaseModel):
    query: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    property_type: Optional[PropertyType] = None
    listing_type: Optional[ListingType] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    min_size: Optional[float] = None
    max_size: Optional[float] = None
    verified_only: bool = False
    page: int = 1
    size: int = 20
