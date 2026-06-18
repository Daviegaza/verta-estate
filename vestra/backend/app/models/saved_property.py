from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

class SavedProperty(Base):
    __tablename__ = "saved_properties"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint("user_id", "property_id"),)

    # Relationships (assuming User and Property models exist)
    # user = relationship("User", backref="saved_properties")
    # property = relationship("Property", backref="saved_by_users")