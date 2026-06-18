from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from enum import Enum

class KYCStatus(str, Enum):
    pending = "pending"
    reviewing = "reviewing"
    approved = "approved"
    rejected = "rejected"

class KYCVerification(Base):
    __tablename__ = "kyc_verifications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(KYCStatus), default=KYCStatus.pending)  # pending/reviewing/approved/rejected
    id_type = Column(String(50))  # national_id, passport, alien_id
    id_number = Column(String(50))
    id_front_url = Column(String(1000))
    id_back_url = Column(String(1000))
    selfie_url = Column(String(1000))
    ocr_data = Column(JSON, default=dict)  # Extracted text from ID
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Annual re-verification
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships (assuming User model exists)
    # user = relationship("User", foreign_keys=[user_id], backref="kyc_verifications")
    # reviewer = relationship("User", foreign_keys=[reviewer_id], remote_side=[id])