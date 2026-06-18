from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class SavedSearch(Base):
    __tablename__ = "saved_searches"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    filters = Column(JSON, default=dict)  # Stored search criteria
    notify_email = Column(Boolean, default=True)
    notify_whatsapp = Column(Boolean, default=False)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships (assuming User model exists)
    # user = relationship("User", backref="saved_searches")