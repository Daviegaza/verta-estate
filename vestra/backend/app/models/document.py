from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class DocumentType(str, enum.Enum):
    title_deed = "title_deed"
    sale_agreement = "sale_agreement"
    lease_agreement = "lease_agreement"
    national_id = "national_id"
    kra_pin = "kra_pin"
    land_search = "land_search"
    rates_clearance = "rates_clearance"
    other = "other"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    is_verified = Column(Boolean, default=False)
    verification_notes = Column(Text, nullable=True)
    
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    property = relationship("Property", back_populates="documents", lazy="selectin")
    uploader = relationship("User", lazy="selectin")


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    approved = "approved"
    flagged = "flagged"
    rejected = "rejected"


class Verification(Base):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(VerificationStatus), default=VerificationStatus.pending)

    # AI Analysis Results
    fraud_risk_score = Column(Float, nullable=True)        # 0-100
    trust_score = Column(Float, nullable=True)             # 0-100
    price_reasonableness = Column(String(20), nullable=True)  # under/fair/over
    ownership_confidence = Column(String(20), nullable=True)  # low/medium/high
    ai_recommendation = Column(String(20), nullable=True)     # approve/review/reject
    document_flags = Column(JSON, default=list)
    ai_summary = Column(Text, nullable=True)
    ai_raw_response = Column(JSON, nullable=True)

    # Human Review
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Report
    report_url = Column(String(1000), nullable=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    property = relationship("Property", back_populates="verifications", lazy="selectin")
    user = relationship("User", back_populates="verifications", lazy="selectin", foreign_keys=[user_id])
    requester = relationship("User", lazy="selectin", foreign_keys=[requester_id])
    reviewer = relationship("User", lazy="selectin", foreign_keys=[reviewed_by_id])
