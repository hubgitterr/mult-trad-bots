import uuid
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Integer, Float
from sqlalchemy.orm import relationship

# Use absolute import from 'backend' root
from core.database import Base

class TradeHistory(Base):
    """
    SQLAlchemy model for storing simulated or actual trade history.
    """
    __tablename__ = "trade_history"

    id = Column(Integer, primary_key=True, index=True)
    # Foreign key linking to the BotConfiguration table
    bot_id = Column(Integer, ForeignKey("bot_configurations.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True) # e.g., 'BTCUSDT'
    action = Column(String, nullable=False) # e.g., 'BUY', 'SELL', 'SIM_BUY', 'SIM_SELL'
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    # Optional: Add fields like order_id (from exchange), fees, pnl, etc.
    # order_id = Column(String, unique=True, index=True, nullable=True)
    # pnl = Column(Float, nullable=True)

    # Define the relationship back to the BotConfiguration model
    bot = relationship("BotConfiguration", back_populates="trade_history")

    def __repr__(self):
        return f"<TradeHistory(id={self.id}, bot_id={self.bot_id}, action='{self.action}', symbol='{self.symbol}', price={self.price}, quantity={self.quantity}, time='{self.timestamp}')>"
