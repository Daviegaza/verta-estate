from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.document import VerificationStatus, DocumentType


class VerificationRequest(BaseModel):
    property_id: int
    phone_number: str  # for M-Pesa payment


class VerificationResponse(BaseModel):
    id: int
    property_id: Optional[int]
    status: VerificationStatus
    fraud_risk_score: Optional[float]
    trust_score: Optional[float]
    price_reasonableness: Optional[str]
    ownership_confidence: Optional[str]
    ai_recommendation: Optional[str]
    document_flags: List[str]
    ai_summary: Optional[str]
    report_url: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    id: int
    property_id: Optional[int]
    document_type: DocumentType
    file_name: str
    file_size: Optional[int]
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MpesaPaymentRequest(BaseModel):
    phone_number: str
    amount: float
    purpose: str
    reference_id: Optional[int] = None


class MpesaCallbackData(BaseModel):
    Body: dict


class PaymentResponse(BaseModel):
    id: int
    amount: float
    currency: str
    method: str
    purpose: str
    status: str
    reference: Optional[str]
    mpesa_checkout_request_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AdminStatsResponse(BaseModel):
    total_users: int
    total_properties: int
    total_verifications: int
    total_revenue: float
    pending_verifications: int
    active_listings: int
    verified_properties: int
    agents_count: int
