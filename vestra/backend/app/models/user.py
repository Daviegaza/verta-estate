from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base
from app.core.encryption import encrypt_field, decrypt_field


class UserRole(str, enum.Enum):
    buyer = "buyer"
    seller = "seller"
    agent = "agent"
    landlord = "landlord"
    admin = "admin"
    super_admin = "super_admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    # phone and national_id are stored encrypted at rest. The plaintext property
    # decrypts on read; the setter encrypts on write. Use _phone / _national_id
    # to bypass the descriptor (e.g. for queries or bulk operations).
    _phone = Column("phone", String(255), unique=True, index=True, nullable=True)
    _national_id = Column("national_id", String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.buyer, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_kyc_verified = Column(Boolean, default=False)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    referral_code = Column(String(20), unique=True, index=True, nullable=True)  # Unique referral code (VST-XXXXXXX)

    # ── TOTP 2FA ────────────────────────────────────────────────────────────
    totp_secret = Column(String(64), nullable=True)       # Base32-encoded TOTP secret
    two_factor_enabled = Column(Boolean, default=False, nullable=False)

    # ── GDPR / Consent tracking ─────────────────────────────────────────────
    consent_marketing = Column(Boolean, default=False, nullable=False)
    consent_data_processing = Column(Boolean, default=False, nullable=False)
    consent_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Auto-encrypt / decrypt phone and national_id ──────────────────────
    # These properties shadow the _phone / _national_id columns so that
    # reading user.phone returns the plaintext and writing user.phone = "..."
    # automatically encrypts before persisting.

    @property
    def phone(self) -> str | None:
        return decrypt_field(self._phone)

    @phone.setter
    def phone(self, value: str | None) -> None:
        self._phone = encrypt_field(value) if value else None

    @property
    def national_id(self) -> str | None:
        return decrypt_field(self._national_id)

    @national_id.setter
    def national_id(self, value: str | None) -> None:
        self._national_id = encrypt_field(value) if value else None

    properties = relationship("Property", back_populates="owner", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="user", foreign_keys="[Verification.user_id]", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    agent_profile = relationship("AgentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"
