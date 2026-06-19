"""
Enterprise & Business models — API keys, coupons, payouts, receipts.
Monetization infrastructure for B2B and B2C revenue streams.
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, Text, JSON,
    Numeric, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


# ── API Keys (Enterprise) ──────────────────────────────────────────────────────

class APIKey(Base):
    """Enterprise API key for programmatic access to VESTRA data."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    key_hash = Column(String(128), nullable=False, unique=True)  # SHA-256 of the key
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for display: "vsk_abc123..."
    scopes = Column(JSON, default=list)
    # Scopes: read:properties, read:verifications, read:analytics,
    #         write:properties, write:verifications
    rate_limit_per_min = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


class WebhookEvent(str, enum.Enum):
    property_created = "property.created"
    property_updated = "property.updated"
    verification_completed = "verification.completed"
    payment_completed = "payment.completed"
    rent_paid = "rent.paid"
    maintenance_updated = "maintenance.updated"
    subscription_created = "subscription.created"
    escrow_completed = "escrow.completed"
    dispute_filed = "dispute.filed"
    referral_rewarded = "referral.rewarded"
    property_verified = "property.verified"
    rental_payment_due = "rental.payment_due"
    payout_processed = "payout.processed"


class Webhook(Base):
    """Outbound webhook registration for enterprise clients."""
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    url = Column(String(1000), nullable=False)
    secret = Column(String(100), nullable=False)  # HMAC signing secret
    events = Column(JSON, default=list)  # List of WebhookEvent values
    is_active = Column(Boolean, default=True)
    failures = Column(Integer, default=0)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")


# ── Coupons / Promo Codes ──────────────────────────────────────────────────────

class DiscountType(str, enum.Enum):
    percentage = "percentage"
    fixed = "fixed"


class Coupon(Base):
    """Discount/promo codes for marketing and growth."""
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    discount_type = Column(Enum(DiscountType), nullable=False)
    discount_value = Column(Numeric(12, 2), nullable=False)  # Percentage or KES amount
    min_purchase_kes = Column(Numeric(12, 2), default=0)
    max_discount_kes = Column(Numeric(12, 2), nullable=True)  # Cap for percentage discounts
    max_uses = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    applies_to = Column(JSON, default=list)  # ["verification", "subscription", "listing", "all"]
    is_active = Column(Boolean, default=True)
    first_time_only = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User")


# ── Payouts ────────────────────────────────────────────────────────────────────

class PayoutStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Payout(Base):
    """Payout/disbursement to agents, landlords, and referrers via M-Pesa B2C."""
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount_kes = Column(Numeric(12, 2), nullable=False)
    type = Column(String(30), nullable=False)  # referral_reward, commission, rent_rebate
    status = Column(Enum(PayoutStatus), default=PayoutStatus.pending, nullable=False)
    mpesa_phone = Column(String(20), nullable=False)
    mpesa_receipt = Column(String(100), nullable=True)
    mpesa_result_code = Column(Integer, nullable=True)
    mpesa_result_desc = Column(String(255), nullable=True)
    reference = Column(String(255), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


# ── Rent Receipts ──────────────────────────────────────────────────────────────

class RentReceipt(Base):
    """Auto-generated rent payment receipts."""
    __tablename__ = "rent_receipts"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("rent_payments.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    receipt_number = Column(String(50), unique=True, nullable=False)
    pdf_url = Column(String(1000), nullable=True)
    amount_kes = Column(Numeric(12, 2), nullable=False)
    month = Column(String(10), nullable=False)  # "2026-06"
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    payment = relationship("RentPayment")
    tenant = relationship("Tenant")


# ── Inspection Reports ─────────────────────────────────────────────────────────

class InspectionType(str, enum.Enum):
    move_in = "move_in"
    move_out = "move_out"
    periodic = "periodic"
    ad_hoc = "ad_hoc"


class InspectionReport(Base):
    """Property inspection reports for rental units."""
    __tablename__ = "inspection_reports"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("rental_units.id"), nullable=False, index=True)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    inspection_type = Column(Enum(InspectionType), default=InspectionType.periodic)
    report_data = Column(JSON, default=dict)  # Room-by-room report
    images = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    unit = relationship("RentalUnit")
    inspector = relationship("User")
