from sqlalchemy.orm import Session
from typing import List, Optional

# Use absolute imports from 'backend' root
from models.trade_history import TradeHistory
from schemas.trade_history import TradeHistoryCreate # Use the create schema

def create_trade_history(db: Session, trade: TradeHistoryCreate) -> TradeHistory:
    """Create a new trade history record."""
    # Note: trade schema already includes bot_id
    db_trade = TradeHistory(**trade.model_dump())
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

def get_trade_history_for_bot(db: Session, bot_id: int, skip: int = 0, limit: int = 1000) -> List[TradeHistory]:
    """Get all trade history records for a specific bot, ordered by time."""
    return (
        db.query(TradeHistory)
        .filter(TradeHistory.bot_id == bot_id)
        .order_by(TradeHistory.timestamp.asc()) # Order chronologically
        .offset(skip)
        .limit(limit)
        .all()
    )

# Optional: Add functions to get specific trades or delete history if needed
# def get_trade(db: Session, trade_id: int) -> Optional[TradeHistory]:
#     return db.query(TradeHistory).filter(TradeHistory.id == trade_id).first()
