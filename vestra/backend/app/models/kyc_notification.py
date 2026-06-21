"""
KYC (Know Your Customer) models — identity verification for all platform users.
Required for agents, landlords, and for high-value transactions.
"""
import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class KYCStatus(enum.StrEnum):
    pending = "pending"
    reviewing = "reviewing"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"  # Needs re-verification


class KYCVerification(Base):
    """Identity verification for a user."""
    __tablename__ = "kyc_verifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(KYCStatus), default=KYCStatus.pending, nullable=False)

    # ID document
    id_type = Column(String(50), nullable=False)  # national_id, passport, alien_id, driving_license
    id_number = Column(String(50), nullable=False)
    id_front_url = Column(String(1000), nullable=True)
    id_back_url = Column(String(1000), nullable=True)
    selfie_url = Column(String(1000), nullable=True)

    # OCR extracted data
    ocr_data = Column(JSON, default=dict)
    ocr_confidence = Column(Integer, nullable=True)  # 0-100

    # Review
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Annual re-verification

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class Notification(Base):
    """In-app and multi-channel notifications."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    # Types: new_listing, price_drop, payment_received, rent_due, rent_overdue,
    #        verification_complete, new_message, maintenance_update, subscription_expiring,
    #        kyc_approved, kyc_rejected, referral_converted, welcome

    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    data = Column(JSON, default=dict)  # Link data: {"property_id": 1, "payment_id": 2, etc.}
    action_url = Column(String(1000), nullable=True)  # Deep-link for notification click
    is_read = Column(Boolean, default=False, index=True)
    channel = Column(String(20), default="in_app")  # in_app, email, whatsapp, sms
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


class Message(Base):
    """Buyer-seller-agent messaging within the platform."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True, index=True)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    property = relationship("Property")


class SavedProperty(Base):
    """User's saved/favorite properties."""
    __tablename__ = "saved_properties"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    property = relationship("Property")

    __table_args__ = (
        UniqueConstraint('user_id', 'property_id', name='uq_saved_property_user_property'),
    )


class SavedSearch(Base):
    """User's saved search criteria with optional alerts."""
    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    filters = Column(JSON, default=dict)  # Stored search criteria
    notify_email = Column(Boolean, default=True)
    notify_whatsapp = Column(Boolean, default=False)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
