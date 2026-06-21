"""
Rental Management Models — apartments, tenants, leases, rent payments, maintenance.
Enables landlords to manage their entire rental portfolio from Vestra.
"""
import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class LeaseStatus(enum.StrEnum):
    active = "active"
    expiring_soon = "expiring_soon"   # Within 30 days
    expired = "expired"
    terminated = "terminated"
    renewed = "renewed"


class RentPaymentStatus(enum.StrEnum):
    pending = "pending"
    paid = "paid"
    late = "late"
    partial = "partial"
    failed = "failed"


class MaintenancePriority(enum.StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    emergency = "emergency"


class MaintenanceStatus(enum.StrEnum):
    reported = "reported"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


# ── Apartment / Unit ──────────────────────────────────────────────────────────

class RentalUnit(Base):
    """A single rental unit (apartment, house, etc.) managed by a landlord."""
    __tablename__ = "rental_units"

    id = Column(Integer, primary_key=True, index=True)
    landlord_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)  # Linked property listing
    building_name = Column(String(200), nullable=True)     # e.g., "Sunset Apartments", "Kilimani Heights"
    name = Column(String(200), nullable=False)             # e.g., "Unit 3B", "Flat 12", "A-204"
    unit_number = Column(String(20), nullable=True)         # e.g., "1A", "2B", "G1", "PH1"
    unit_type = Column(String(50), nullable=False)          # bedsitter, 1br, 2br, 3br, studio, penthouse
    bedrooms = Column(Integer, default=1)
    bathrooms = Column(Integer, default=1)
    floor = Column(Integer, nullable=True)
    size_sqft = Column(Float, nullable=True)
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False)
    county = Column(String(100), nullable=False, default="")
    monthly_rent_kes = Column(Numeric(12, 2), nullable=False)
    deposit_kes = Column(Numeric(12, 2), default=0)
    water_kes = Column(Numeric(10, 2), default=0)          # Monthly water bill
    electricity_kes = Column(Numeric(10, 2), default=0)     # Monthly electricity
    service_charge_kes = Column(Numeric(10, 2), default=0)  # Service charge / HOA
    is_occupied = Column(Boolean, default=False)
    amenities = Column(JSON, default=list)                 # ["parking", "gym", "lift", "cctv", "borehole"]
    images = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    landlord = relationship("User")
    property = relationship("Property")
    leases = relationship("Lease", back_populates="unit", cascade="all, delete-orphan")
    tenants = relationship("Tenant", back_populates="unit", cascade="all, delete-orphan")


# ── Tenant ────────────────────────────────────────────────────────────────────

class Tenant(Base):
    """A tenant renting a unit."""
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("rental_units.id"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=False)          # For M-Pesa rent payments
    national_id = Column(String(50), nullable=True)
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    employer = Column(String(255), nullable=True)
    move_in_date = Column(DateTime(timezone=True), nullable=False)
    move_out_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    rent_due_day = Column(Integer, default=1)            # Day of month rent is due
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    unit = relationship("RentalUnit", back_populates="tenants")
    lease = relationship("Lease", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    payments = relationship("RentPayment", back_populates="tenant", cascade="all, delete-orphan")


# ── Lease ─────────────────────────────────────────────────────────────────────

class Lease(Base):
    """Lease agreement between landlord and tenant."""
    __tablename__ = "leases"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("rental_units.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, unique=True)
    status = Column(Enum(LeaseStatus), default=LeaseStatus.active)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    monthly_rent_kes = Column(Numeric(12, 2), nullable=False)
    deposit_kes = Column(Numeric(12, 2), default=0)
    deposit_paid = Column(Boolean, default=False)
    lease_document_url = Column(String(1000), nullable=True)
    terms = Column(Text, nullable=True)
    auto_renew = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    unit = relationship("RentalUnit", back_populates="leases")
    tenant = relationship("Tenant", back_populates="lease")


# ── Rent Payment ──────────────────────────────────────────────────────────────

class RentPayment(Base):
    """Individual rent payment record."""
    __tablename__ = "rent_payments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("rental_units.id"), nullable=False)
    lease_id = Column(Integer, ForeignKey("leases.id"), nullable=True)
    amount_kes = Column(Numeric(12, 2), nullable=False)
    amount_paid_kes = Column(Numeric(12, 2), default=0)
    status = Column(Enum(RentPaymentStatus), default=RentPaymentStatus.pending)
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_date = Column(DateTime(timezone=True), nullable=True)
    payment_method = Column(String(20), default="mpesa")
    mpesa_receipt = Column(String(100), nullable=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)  # Link to payment table
    month = Column(String(10), nullable=False)          # "2026-06"
    late_fee_kes = Column(Numeric(12, 2), default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="payments")
    unit = relationship("RentalUnit")


# ── Payment Arrangement (Flexible Payment Plan) ────────────────────────────────

class ArrangementStatus(enum.StrEnum):
    requested = "requested"
    approved = "approved"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"
    declined = "declined"


class PaymentArrangement(Base):
    """
    Flexible payment plan for tenants who need to split rent into installments.
    Example: A tenant owing KES 30,000 can pay KES 10,000 on 5th, 15th, and 25th
    instead of all at once on the 1st.
    """
    __tablename__ = "payment_arrangements"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("rental_units.id"), nullable=False)
    lease_id = Column(Integer, ForeignKey("leases.id"), nullable=True)
    total_amount_kes = Column(Numeric(12, 2), nullable=False)
    remaining_balance_kes = Column(Numeric(12, 2), nullable=False)
    number_of_installments = Column(Integer, nullable=False)
    installments_paid = Column(Integer, default=0)
    status = Column(Enum(ArrangementStatus), default=ArrangementStatus.requested)
    reason = Column(Text, nullable=True)  # Tenant's reason for requesting arrangement
    landlord_notes = Column(Text, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)  # Must be within the month
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tenant = relationship("Tenant")


class InstallmentPayment(Base):
    """Individual installment within a payment arrangement."""
    __tablename__ = "installment_payments"

    id = Column(Integer, primary_key=True, index=True)
    arrangement_id = Column(Integer, ForeignKey("payment_arrangements.id"), nullable=False, index=True)
    amount_kes = Column(Numeric(12, 2), nullable=False)
    amount_paid_kes = Column(Numeric(12, 2), default=0)
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="pending")  # pending, paid, late, skipped
    mpesa_receipt = Column(String(100), nullable=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    arrangement = relationship("PaymentArrangement")


# ── Rent Collection Configuration (per lease) ──────────────────────────────────

class RentCollectionConfig(Base):
    """
    Per-lease configuration for rent collection flexibility.
    Allows landlords to set custom grace periods, late fee structures,
    and enable/disable auto-collection features.
    """
    __tablename__ = "rent_collection_configs"

    id = Column(Integer, primary_key=True, index=True)
    lease_id = Column(Integer, ForeignKey("leases.id"), nullable=False, unique=True)
    grace_period_days = Column(Integer, default=5)  # Days after due date before late fees
    late_fee_type = Column(String(20), default="fixed")  # fixed, percentage, none
    late_fee_amount_kes = Column(Numeric(12, 2), default=100)  # Fixed late fee per day
    late_fee_percent = Column(Numeric(5, 2), default=2.0)  # Percentage of rent
    late_fee_max_kes = Column(Numeric(12, 2), default=3000)  # Cap on late fees
    allow_partial_payments = Column(Boolean, default=True)  # Accept partial rent payments
    allow_payment_arrangements = Column(Boolean, default=True)  # Allow installment plans
    auto_apply_late_fees = Column(Boolean, default=True)
    reminders_enabled = Column(Boolean, default=True)
    reminder_days_before = Column(JSON, default=[3, 1])  # e.g., remind 3 days and 1 day before
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    lease = relationship("Lease")


# ── Maintenance Request ───────────────────────────────────────────────────────

class MaintenanceRequest(Base):
    """Maintenance request from tenant to landlord."""
    __tablename__ = "maintenance_requests"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("rental_units.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Enum(MaintenancePriority), default=MaintenancePriority.medium)
    status = Column(Enum(MaintenanceStatus), default=MaintenanceStatus.reported)
    category = Column(String(50), nullable=True)       # plumbing, electrical, structural, appliance, other
    assigned_to = Column(String(255), nullable=True)    # Contractor/vendor name
    estimated_cost_kes = Column(Numeric(12, 2), nullable=True)
    actual_cost_kes = Column(Numeric(12, 2), nullable=True)
    images = Column(JSON, default=list)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    unit = relationship("RentalUnit")
    tenant = relationship("Tenant")
