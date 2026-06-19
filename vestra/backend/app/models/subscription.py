"""
Subscription model — tracks paid subscriptions for sellers, agents, and landlords.
Buyers are always FREE.
"""
from __future__ import annotations

import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Float, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class SubscriptionTier(str, enum.Enum):
    free = "free"
    basic = "basic"
    pro = "pro"
    premium = "premium"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    past_due = "past_due"        # Payment failed, in grace period
    cancelled = "cancelled"
    expired = "expired"
    trialing = "trialing"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.free, nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.active, nullable=False)

    # Billing
    amount_kes = Column(Numeric(12, 2), nullable=False)  # Monthly price
    billing_cycle = Column(String(20), default="monthly")  # monthly / annual
    auto_renew = Column(Boolean, default=True)
    payment_method = Column(String(20), default="mpesa")    # mpesa / stripe

    # Dates
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    grace_period_end = Column(DateTime(timezone=True), nullable=True)  # +3 days after period end
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)

    # M-Pesa auto-renew
    mpesa_phone = Column(String(20), nullable=True)
    last_payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    renewal_failures = Column(Integer, default=0)       # Consecutive failed renewals
    max_renewal_failures = Column(Integer, default=3)    # Cancel after this many failures

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    last_payment = relationship("Payment", foreign_keys=[last_payment_id])

    def __repr__(self):
        return f"<Subscription #{self.id} user={self.user_id} tier={self.tier.value} status={self.status.value}>"
