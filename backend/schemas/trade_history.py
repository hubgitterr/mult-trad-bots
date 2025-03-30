from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional

# Import BotConfiguration schema for relationship definition if needed
# from .bot_configuration import BotConfiguration # Or use 'BotConfiguration'

# Shared properties
class TradeHistoryBase(BaseModel):
    symbol: str = Field(..., example="BTCUSDT")
    action: str = Field(..., example="BUY")
    price: float = Field(..., example=50000.50)
    quantity: float = Field(..., example=0.01)
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow) # Default to now if not provided

# Properties to receive via API on creation
class TradeHistoryCreate(TradeHistoryBase):
    bot_id: int # Must be provided when creating a history record
    pass

# Properties to receive via API on update (likely not needed for trade history)
# class TradeHistoryUpdate(BaseModel):
#     pass

# Properties shared by models stored in DB
class TradeHistoryInDBBase(TradeHistoryBase):
    id: int
    bot_id: int
    timestamp: datetime # In DB, timestamp is not optional

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode

# Properties to return to client
class TradeHistory(TradeHistoryInDBBase):
    # Optionally include bot details if needed
    # bot: Optional[BotConfiguration] = None # Requires BotConfiguration schema definition/import
    pass

# Properties stored in DB
class TradeHistoryInDB(TradeHistoryInDBBase):
    pass
