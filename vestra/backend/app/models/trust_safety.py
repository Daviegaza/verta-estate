"""
Trust & Safety models: reviews, escrow, disputes, and fraud reports.
These models build the trust infrastructure that makes VESTRA defensible.
"""
import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Review(Base):
    """User review of an agent, landlord, or property."""

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    rating = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    is_verified_transaction = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    reviewer = relationship("User", foreign_keys=[reviewer_id], lazy="selectin")
    subject = relationship("User", foreign_keys=[subject_id], lazy="selectin")
    property = relationship("Property", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "reviewer_id",
            "subject_id",
            "property_id",
            name="uq_review_per_user",
        ),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_1_5"),
        CheckConstraint("reviewer_id <> subject_id", name="ck_reviews_no_self_review"),
        Index("ix_reviews_subject_created", "subject_id", "created_at"),
    )


class EscrowStatus(str, enum.Enum):
    initiated = "initiated"
    deposit_paid = "deposit_paid"
    balance_paid = "balance_paid"
    completed = "completed"
    cancelled = "cancelled"
    refunded = "refunded"
    disputed = "disputed"


class EscrowTransaction(Base):
    """Secure transaction holding for property purchases."""

    __tablename__ = "escrow_transactions"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount_kes = Column(Numeric(12, 2), nullable=False)
    deposit_amount_kes = Column(Numeric(12, 2), nullable=True)
    status = Column(Enum(EscrowStatus), default=EscrowStatus.initiated, nullable=False)
    payment_reference = Column(String(255), nullable=True)
    release_condition_met = Column(Boolean, default=False)
    completion_date = Column(DateTime(timezone=True), nullable=True)
    terms = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    property = relationship("Property", lazy="selectin")
    buyer = relationship("User", foreign_keys=[buyer_id], lazy="selectin")
    seller = relationship("User", foreign_keys=[seller_id], lazy="selectin")
    agent = relationship("User", foreign_keys=[agent_id], lazy="selectin")

    __table_args__ = (
        CheckConstraint("amount_kes > 0", name="ck_escrow_amount_positive"),
        CheckConstraint(
            "deposit_amount_kes IS NULL OR deposit_amount_kes >= 0",
            name="ck_escrow_deposit_non_negative",
        ),
        CheckConstraint(
            "deposit_amount_kes IS NULL OR deposit_amount_kes <= amount_kes",
            name="ck_escrow_deposit_not_above_total",
        ),
        CheckConstraint("buyer_id <> seller_id", name="ck_escrow_buyer_not_seller"),
        Index("ix_escrow_status_created", "status", "created_at"),
    )


class DisputeStatus(str, enum.Enum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    closed = "closed"


class Dispute(Base):
    """User dispute: fraud, misrepresentation, payment issues, etc."""

    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    subject_type = Column(String(50), nullable=True)
    subject_id = Column(Integer, nullable=True)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    evidence_urls = Column(JSON, default=list)
    status = Column(Enum(DisputeStatus), default=DisputeStatus.open, nullable=False)
    resolution = Column(Text, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reporter = relationship("User", foreign_keys=[reporter_id], lazy="selectin")
    resolved_by = relationship("User", foreign_keys=[resolved_by_id], lazy="selectin")
    property = relationship("Property", lazy="selectin")

    __table_args__ = (
        Index("ix_disputes_status_created", "status", "created_at"),
        Index("ix_disputes_subject", "subject_type", "subject_id"),
    )


class FraudReportStatus(str, enum.Enum):
    pending = "pending"
    investigating = "investigating"
    confirmed = "confirmed"
    false_report = "false_report"


class FraudReport(Base):
    """Crowdsourced fraud intelligence blacklist of bad actors."""

    __tablename__ = "fraud_reports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reported_phone = Column(String(20), nullable=True, index=True)
    reported_email = Column(String(255), nullable=True, index=True)
    reported_title_deed = Column(String(100), nullable=True, index=True)
    reported_name = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=False)
    evidence_urls = Column(JSON, default=list)
    status = Column(Enum(FraudReportStatus), default=FraudReportStatus.pending, nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reporter = relationship("User", foreign_keys=[reporter_id], lazy="selectin")
    reviewer = relationship("User", foreign_keys=[reviewed_by_id], lazy="selectin")

    __table_args__ = (
        Index("ix_fraud_reports_status_created", "status", "created_at"),
        CheckConstraint(
            "reported_phone IS NOT NULL OR reported_email IS NOT NULL OR "
            "reported_title_deed IS NOT NULL OR reported_name IS NOT NULL",
            name="ck_fraud_reports_has_identifier",
        ),
    )
