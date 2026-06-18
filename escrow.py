from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, func, Boolean
from app.core.database import Base

class EscrowTransaction(Base):
    __tablename__ = "escrow_transactions"
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Agent involved in the transaction
    amount_kes = Column(Numeric(12, 2), nullable=False)
    deposit_amount_kes = Column(Numeric(12, 2), nullable=True) # Initial deposit amount
    status = Column(String(30), default="initiated") # initiated, funded, released, disputed, refunded
    
    payment_reference = Column(String(255), nullable=True) # Not necessarily unique, can be multiple payments
    release_condition_met = Column(Boolean, default=False)
    completion_date = Column(DateTime(timezone=True), nullable=True) # Date transaction is expected to complete
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())