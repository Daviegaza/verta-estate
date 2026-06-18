"""
Analytics & Data Collection models — user behavior tracking, price history,
verification outcomes. Foundation for future ML models.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, JSON, Numeric, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class UserEvent(Base):
    """User behavior event tracking for analytics and ML training."""
    __tablename__ = "user_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    # Types: search, view, inquiry, favorite, share, report_view,
    #        listing_create, verification_start, payment_initiate,
    #        comparison_view, whatsapp_share, referral_copy
    event_data = Column(JSON, default=dict)
    client_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", lazy="selectin")


class PriceChange(Base):
    """Track all price changes for ML price prediction models."""
    __tablename__ = "price_changes"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    old_price = Column(Numeric(12, 2), nullable=False)
    new_price = Column(Numeric(12, 2), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    property = relationship("Property", lazy="selectin")
    changed_by = relationship("User", lazy="selectin")


class VerificationOutcome(Base):
    """Track AI predictions vs human decisions for model evaluation."""
    __tablename__ = "verification_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    verification_id = Column(Integer, ForeignKey("verifications.id"), nullable=False, index=True)
    ai_prediction = Column(JSON, default=dict)  # AI's prediction
    human_decision = Column(String(20), nullable=False)  # approved / rejected / flagged
    was_correct = Column(Boolean, nullable=True)  # AI correct?
    ground_truth_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    verification = relationship("Verification", lazy="selectin")


class SearchAnalytics(Base):
    """Track search queries and results for search relevance improvement."""
    __tablename__ = "search_analytics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    query = Column(String(500), nullable=False, index=True)
    filters_applied = Column(JSON, default=dict)
    results_count = Column(Integer, default=0)
    clicked_property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    session_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", lazy="selectin")
    clicked_property = relationship("Property", lazy="selectin")
