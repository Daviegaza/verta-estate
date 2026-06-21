"""
Audit log model — tracks all state-changing operations for compliance & security.
"""
from __future__ import annotations

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)  # e.g. "user.created", "property.verified"
    resource_type = Column(String(50), nullable=False, index=True)  # e.g. "user", "property", "payment"
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)  # before/after diffs, metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    correlation_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.resource_type}#{self.resource_id}>"
