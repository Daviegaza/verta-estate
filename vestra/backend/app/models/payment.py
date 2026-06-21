import enum

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PaymentStatus(enum.StrEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class PaymentMethod(enum.StrEnum):
    mpesa = "mpesa"
    stripe = "stripe"
    bank_transfer = "bank_transfer"
    paypal = "paypal"
    airtel_money = "airtel_money"
    crypto = "crypto"


class PaymentPurpose(enum.StrEnum):
    verification_report = "verification_report"
    agent_badge = "agent_badge"
    listing_fee = "listing_fee"
    subscription = "subscription"
    transaction_fee = "transaction_fee"
    rent = "rent"
    deposit = "deposit"
    utility = "utility"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="KES")
    method = Column(Enum(PaymentMethod), nullable=False)
    purpose = Column(Enum(PaymentPurpose), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending)

    # M-Pesa specific
    mpesa_checkout_request_id = Column(String(255), nullable=True)
    mpesa_merchant_request_id = Column(String(255), nullable=True)
    mpesa_receipt_number = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)

    # Stripe specific
    stripe_payment_intent_id = Column(String(255), nullable=True)
    stripe_charge_id = Column(String(255), nullable=True)

    # General
    reference = Column(String(255), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    payment_metadata = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.reference} {self.amount} {self.currency}>"
