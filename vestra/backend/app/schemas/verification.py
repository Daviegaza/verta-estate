from datetime import datetime

from pydantic import BaseModel

from app.models.document import DocumentType, VerificationStatus


class VerificationRequest(BaseModel):
    property_id: int
    phone_number: str  # for M-Pesa payment


class VerificationResponse(BaseModel):
    id: int
    property_id: int | None
    status: VerificationStatus
    fraud_risk_score: float | None
    trust_score: float | None
    price_reasonableness: str | None
    ownership_confidence: str | None
    ai_recommendation: str | None
    document_flags: list[str]
    ai_summary: str | None
    report_url: str | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    id: int
    property_id: int | None
    document_type: DocumentType
    file_name: str
    file_size: int | None
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MpesaPaymentRequest(BaseModel):
    phone_number: str
    amount: float
    purpose: str
    reference_id: int | None = None


class MpesaCallbackData(BaseModel):
    Body: dict


class PaymentResponse(BaseModel):
    id: int
    amount: float
    currency: str
    method: str
    purpose: str
    status: str
    reference: str | None
    mpesa_checkout_request_id: str | None
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
