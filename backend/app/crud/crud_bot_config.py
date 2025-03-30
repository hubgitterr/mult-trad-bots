import uuid
from sqlalchemy.orm import Session
from typing import List, Optional

# Use absolute imports from 'backend' root
from models.bot_configuration import BotConfiguration
from schemas.bot_configuration import BotConfigurationCreate, BotConfigurationUpdate

def get_bot_config(db: Session, bot_id: int, user_id: uuid.UUID) -> Optional[BotConfiguration]:
    """Get a single bot configuration by ID, ensuring it belongs to the user."""
    return db.query(BotConfiguration).filter(BotConfiguration.id == bot_id, BotConfiguration.user_id == user_id).first()

def get_bot_configs_by_user(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[BotConfiguration]:
    """Get all bot configurations for a specific user."""
    return db.query(BotConfiguration).filter(BotConfiguration.user_id == user_id).offset(skip).limit(limit).all()

def create_bot_config(db: Session, bot_config: BotConfigurationCreate, user_id: uuid.UUID) -> BotConfiguration:
    """Create a new bot configuration."""
    db_bot_config = BotConfiguration(
        **bot_config.model_dump(), # Use model_dump() for Pydantic v2
        user_id=user_id
    )
    db.add(db_bot_config)
    db.commit()
    db.refresh(db_bot_config)
    return db_bot_config

def update_bot_config(db: Session, bot_id: int, bot_config_update: BotConfigurationUpdate, user_id: uuid.UUID) -> Optional[BotConfiguration]:
    """Update an existing bot configuration."""
    db_bot_config = get_bot_config(db, bot_id, user_id)
    if not db_bot_config:
        return None

    update_data = bot_config_update.model_dump(exclude_unset=True) # Get only fields that were actually set
    for key, value in update_data.items():
        setattr(db_bot_config, key, value)

    db.add(db_bot_config)
    db.commit()
    db.refresh(db_bot_config)
    return db_bot_config

def get_active_bot_configs(db: Session) -> List[BotConfiguration]:
    """Get all bot configurations that are marked as active."""
    # This fetches active bots across ALL users. Modify if only specific user's active bots are needed by the scheduler.
    return db.query(BotConfiguration).filter(BotConfiguration.is_active == True).all()

def delete_bot_config(db: Session, bot_id: int, user_id: uuid.UUID) -> Optional[BotConfiguration]:
    """Delete a bot configuration."""
    db_bot_config = get_bot_config(db, bot_id, user_id)
    if not db_bot_config:
        return None

    db.delete(db_bot_config)
    db.commit()
    return db_bot_config
