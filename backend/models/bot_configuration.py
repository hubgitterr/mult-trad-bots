import uuid
from sqlalchemy import Column, String, Boolean, DateTime, func, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# Use absolute import from 'backend' root
from core.database import Base

class BotConfiguration(Base):
    """
    SQLAlchemy model for storing trading bot configurations.
    """
    __tablename__ = "bot_configurations"

    id = Column(Integer, primary_key=True, index=True) # Simple integer ID for this table
    # Foreign key linking to the User table (using the UUID primary key of User)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    bot_type = Column(String, index=True, nullable=False) # e.g., 'momentum', 'grid', 'dca'
    name = Column(String, nullable=False, default="Unnamed Bot") # User-friendly name
    settings = Column(JSON, nullable=False) # Store bot-specific parameters (symbol, indicators, grid levels etc.)
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Define the relationship back to the User model
    owner = relationship("User", back_populates="bots")

    # Define the relationship to the TradeHistory model
    # 'cascade="all, delete-orphan"' means if a bot config is deleted, its trade history is also deleted.
    trade_history = relationship("TradeHistory", back_populates="bot", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BotConfiguration(id={self.id}, name='{self.name}', type='{self.bot_type}', user_id={self.user_id}, active={self.is_active})>"
