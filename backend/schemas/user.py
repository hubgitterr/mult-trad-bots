import uuid
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime
from typing import Optional, List

# Forward declaration for BotConfiguration schema if needed for relationships
# (Not strictly necessary for this basic User schema, but good practice)
# class BotConfiguration(BaseModel):
#     pass

# Shared properties
class UserBase(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    # Add other base fields if needed, e.g., full_name: Optional[str] = None

# Properties to receive via API on creation
# We might not need a dedicated UserCreate if Supabase handles creation,
# but it's useful if we sync users to our DB manually.
class UserCreate(UserBase):
    # Supabase ID might be provided if syncing after Supabase auth creation
    id: Optional[uuid.UUID] = None
    # Password is not stored here; handled by Supabase Auth
    pass

# Properties to receive via API on update (example)
# class UserUpdate(UserBase):
#     full_name: Optional[str] = None
#     # Email update might be restricted or handled via Supabase directly

# Properties shared by models stored in DB
class UserInDBBase(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode

# Properties to return to client
class User(UserInDBBase):
    # Include relationships if needed, e.g.:
    # bots: List['BotConfiguration'] = [] # Requires BotConfiguration schema definition/import
    pass

# Properties stored in DB
class UserInDB(UserInDBBase):
    pass

# Example of how BotConfiguration schema might look if needed here
# from .bot_configuration import BotConfigurationBase # Assuming BotConfigurationBase exists
# class UserWithBots(User):
#     bots: List[BotConfigurationBase] = []
