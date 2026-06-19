"""
Rental Management Models — apartments, tenants, leases, rent payments, maintenance.
Enables landlords to manage their entire rental portfolio from Vestra.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Float, Numeric, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class LeaseStatus(str, enum.Enum):
    active = "active"
    expiring_soon = "expiring_soon"   # Within 30 days
    expired = "expired"
    terminated = "terminated"
    renewed = "renewed"


class RentPaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    late = "late"
    partial = "partial"
    failed = "failed"


class MaintenancePriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    emergency = "emergency"


class MaintenanceStatus(str, enum.Enum):
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
    name = Column(String(200), nullable=False)       # e.g., "Unit 3B" or "Kilimani Apt #4"
    unit_type = Column(String(50), nullable=False)   # apartment, house, studio, bedsitter
    bedrooms = Column(Integer, default=1)
    bathrooms = Column(Integer, default=1)
    floor = Column(Integer, nullable=True)
    size_sqft = Column(Float, nullable=True)
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False)
    county = Column(String(100), nullable=False, default="")
    monthly_rent_kes = Column(Numeric(12, 2), nullable=False)
    deposit_kes = Column(Numeric(12, 2), default=0)
    is_occupied = Column(Boolean, default=False)
    amenities = Column(JSON, default=list)
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
