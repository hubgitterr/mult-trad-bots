import uuid
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any, List

# Import User schema for relationship definition
# Use forward reference if User schema imports this one to avoid circular imports
from .user import User # Or use: 'User' if needed

# Shared properties
class BotConfigurationBase(BaseModel):
    bot_type: str = Field(..., example="momentum")
    name: str = Field(..., example="My BTC Momentum Bot")
    settings: Dict[str, Any] = Field(..., example={"symbol": "BTCUSDT", "rsi_period": 14, "ma_short": 9, "ma_long": 21})
    is_active: bool = Field(default=False)

# Properties to receive via API on creation
class BotConfigurationCreate(BotConfigurationBase):
    # user_id will be set based on the authenticated user in the API endpoint
    pass

# Properties to receive via API on update
class BotConfigurationUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

# Properties shared by models stored in DB
class BotConfigurationInDBBase(BotConfigurationBase):
    id: int
    user_id: uuid.UUID # Assuming user_id in DB is UUID from User model
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode

# Properties to return to client
class BotConfiguration(BotConfigurationInDBBase):
    # Optionally include owner details if needed
    # owner: Optional[User] = None # Requires User schema definition/import
    pass

# Properties stored in DB
class BotConfigurationInDB(BotConfigurationInDBBase):
    pass
