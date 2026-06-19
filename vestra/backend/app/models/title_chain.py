"""TitleChain Block model — immutable property title history."""
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class TitleChainBlock(Base):
    __tablename__ = "title_chain_blocks"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    block_index = Column(Integer, nullable=False)
    timestamp = Column(String(50), nullable=False)
    event_type = Column(String(30), nullable=False, index=True)
    data = Column(JSON, default=dict)
    previous_hash = Column(String(64), nullable=False)
    block_hash = Column(String(64), nullable=False, unique=True)
    validator = Column(String(50), default="VESTRA_AI")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    property = relationship("Property")
