from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, Text,
    Float, Numeric, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class PropertyType(str, enum.Enum):
    residential = "residential"
    commercial = "commercial"
    land = "land"
    industrial = "industrial"
    agricultural = "agricultural"
    student_housing = "student_housing"
    short_stay = "short_stay"


class ListingType(str, enum.Enum):
    sale = "sale"
    rent = "rent"
    lease = "lease"


class PropertyStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    active = "active"
    suspended = "suspended"
    sold = "sold"
    rented = "rented"


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    property_type = Column(Enum(PropertyType), nullable=False)
    listing_type = Column(Enum(ListingType), nullable=False)
    status = Column(Enum(PropertyStatus), default=PropertyStatus.draft)

    # Location
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False)
    county = Column(String(100), nullable=False)
    country = Column(String(100), default="Kenya")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Pricing
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="KES")
    price_negotiable = Column(Boolean, default=False)

    # Details
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    size_sqft = Column(Float, nullable=True)
    year_built = Column(Integer, nullable=True)
    amenities = Column(JSON, default=list)
    images = Column(JSON, default=list)

    # Trust
    trust_score = Column(Float, nullable=True)
    is_verified = Column(Boolean, default=False)
    verification_badge = Column(String(50), nullable=True)

    # Featured listing (paid placement)
    is_featured = Column(Boolean, default=False)
    featured_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Stats
    views = Column(Integer, default=0)
    inquiries = Column(Integer, default=0)

    # Safety
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="properties")
    documents = relationship("Document", back_populates="property", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="property", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Property {self.title}>"


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    agency_name = Column(String(255), nullable=True)
    license_number = Column(String(100), nullable=True)
    years_experience = Column(Integer, default=0)
    specialization = Column(JSON, default=list)
    badge_level = Column(String(50), nullable=True)  # bronze, silver, gold, platinum
    badge_expires_at = Column(DateTime(timezone=True), nullable=True)
    total_listings = Column(Integer, default=0)
    successful_deals = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    subscription_tier = Column(String(50), default="free")
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="agent_profile")
