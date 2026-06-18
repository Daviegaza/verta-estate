from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # new_listing, price_drop, payment_received, rent_due, etc.
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    data = Column(JSON, default=dict)  # Link data (property_id, payment_id, etc.)
    is_read = Column(Boolean, default=False)
    channel = Column(String(20), default="in_app")  # in_app, email, whatsapp, sms
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships (assuming User model exists)
    # user = relationship("User", backref="notifications")