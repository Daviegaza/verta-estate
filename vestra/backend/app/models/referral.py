"""Referral model — viral growth engine."""
import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ReferralStatus(enum.StrEnum):
    signed_up = "signed_up"
    verified = "verified"
    converted = "converted"
    paid_out = "paid_out"


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    referred_user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    referral_code = Column(String(20), nullable=False)
    status = Column(String(20), default=ReferralStatus.signed_up.value)
    rewards_earned = Column(Numeric(12, 2), default=0.0)
    total_rewards = Column(Numeric(12, 2), default=0.0)
    signup_at = Column(DateTime(timezone=True), server_default=func.now())
    converted_at = Column(DateTime(timezone=True), nullable=True)

    referrer = relationship("User", foreign_keys=[referrer_id])
    referred_user = relationship("User", foreign_keys=[referred_user_id])


class ReferralReward(Base):
    __tablename__ = "referral_rewards"

    id = Column(Integer, primary_key=True, index=True)
    referral_id = Column(Integer, ForeignKey("referrals.id"), nullable=False)
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)
    amount_kes = Column(Numeric(12, 2), nullable=False)
    reward_type = Column(String(20), default="credit")  # credit or cash
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    referral = relationship("Referral")
