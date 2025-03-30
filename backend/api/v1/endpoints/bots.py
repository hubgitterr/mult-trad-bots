import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Path, Body, Query
from sqlalchemy.orm import Session
from typing import List, Any, Dict

# Use absolute imports from 'backend' root
from core.database import get_db
from core.auth import get_current_user
from schemas import bot_configuration as bot_schemas
from schemas import trade_history as trade_schemas
from app.crud import crud_bot_config
from app.crud import crud_trade_history
from app.services.performance_calculator import calculate_performance_metrics
from models.bot_configuration import BotConfiguration
from bots.momentum_bot import get_momentum_signal
from bots.grid_bot import get_grid_actions
from bots.dca_bot import get_dca_actions
from core.binance_client import get_binance_client, Client

router = APIRouter()

@router.post(
    "/",
    response_model=bot_schemas.BotConfiguration,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Bot Configuration"
)
def create_bot(
    *,
    db: Session = Depends(get_db),
    bot_in: bot_schemas.BotConfigurationCreate,
    current_user: dict = Depends(get_current_user) # Protected route
):
    """
    Create a new bot configuration for the currently authenticated user.
    """
    user_id_uuid = uuid.UUID(current_user["id"]) # Convert user ID string from token to UUID
    # TODO: Add validation for bot_type and settings based on the type
    # e.g., ensure momentum bot has RSI settings, grid bot has limits, etc.
    db_bot = crud_bot_config.create_bot_config(db=db, bot_config=bot_in, user_id=user_id_uuid)
    return db_bot

@router.get(
    "/",
    response_model=List[bot_schemas.BotConfiguration],
    summary="List User's Bot Configurations"
)
def read_bots(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: dict = Depends(get_current_user) # Protected route
):
    """
    Retrieve all bot configurations for the currently authenticated user.
    """
    user_id_uuid = uuid.UUID(current_user["id"])
    bots = crud_bot_config.get_bot_configs_by_user(db, user_id=user_id_uuid, skip=skip, limit=limit)
    return bots

@router.get(
    "/{bot_id}",
    response_model=bot_schemas.BotConfiguration,
    summary="Get Specific Bot Configuration"
)
def read_bot(
    *,
    db: Session = Depends(get_db),
    bot_id: int = Path(..., title="The ID of the bot to get", ge=1),
    current_user: dict = Depends(get_current_user) # Protected route
):
    """
    Retrieve details of a specific bot configuration owned by the user.
    """
    user_id_uuid = uuid.UUID(current_user["id"])
    db_bot = crud_bot_config.get_bot_config(db, bot_id=bot_id, user_id=user_id_uuid)
    if db_bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot configuration not found")
    return db_bot

@router.put(
    "/{bot_id}",
    response_model=bot_schemas.BotConfiguration,
    summary="Update Bot Configuration"
)
def update_bot(
    *,
    db: Session = Depends(get_db),
    bot_id: int = Path(..., title="The ID of the bot to update", ge=1),
    bot_in: bot_schemas.BotConfigurationUpdate,
    current_user: dict = Depends(get_current_user) # Protected route
):
    """
    Update a specific bot configuration owned by the user.
    """
    user_id_uuid = uuid.UUID(current_user["id"])
    # TODO: Add validation for updated settings based on bot_type if type isn't changing
    db_bot = crud_bot_config.update_bot_config(db, bot_id=bot_id, bot_config_update=bot_in, user_id=user_id_uuid)
    if db_bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot configuration not found")
    return db_bot

@router.delete(
    "/{bot_id}",
    response_model=bot_schemas.BotConfiguration, # Return the deleted bot info
    summary="Delete Bot Configuration"
)
def delete_bot(
    *,
    db: Session = Depends(get_db),
    bot_id: int = Path(..., title="The ID of the bot to delete", ge=1),
    current_user: dict = Depends(get_current_user) # Protected route
):
    """
    Delete a specific bot configuration owned by the user.
    """
    user_id_uuid = uuid.UUID(current_user["id"])
    db_bot = crud_bot_config.delete_bot_config(db, bot_id=bot_id, user_id=user_id_uuid)
    if db_bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot configuration not found")
    # Note: Associated trade history might be deleted due to cascade settings in the model
    return db_bot


# --- Bot Status Endpoint ---

@router.get(
    "/{bot_id}/status",
    response_model=Dict[str, Any], # Return type can be more specific later
    summary="Get Current Bot Status/Signal"
)
def get_bot_status(
    *,
    db: Session = Depends(get_db),
    bot_id: int = Path(..., title="The ID of the bot to check", ge=1),
    current_user: dict = Depends(get_current_user), # Protected route
    binance_client: Client = Depends(get_binance_client) # Inject Binance client
):
    """
    Retrieves the current calculated signal or state for a specific bot
    based on its configuration and live market data. Does not execute trades.
    """
    user_id_uuid = uuid.UUID(current_user["id"])
    # First check if bot exists and belongs to user
    db_bot = crud_bot_config.get_bot_config(db, bot_id=bot_id, user_id=user_id_uuid)
    if db_bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot configuration not found")

    if not binance_client:
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Binance client not available")

    bot_type = db_bot.bot_type
    config = db_bot.settings # Settings are stored as JSON in the DB
    symbol = config.get('symbol', 'UNKNOWN') # Get symbol for context

    status_result: Dict[str, Any] = {
        "bot_id": bot_id,
        "bot_type": bot_type,
        "symbol": symbol,
        "is_active": db_bot.is_active,
        "status": "unknown", # Default status
        "details": {}
    }

    try:
        if bot_type == "momentum":
            # Pass db session and bot_id for potential trade recording (simulation)
            # TODO: Update get_momentum_signal signature if needed
            signal = get_momentum_signal(config, binance_client) # Pass db, bot_id if needed
            status_result["status"] = "signal_generated"
            status_result["details"] = {"signal": signal}
        elif bot_type == "grid":
            # Grid bot needs current price
            ticker = binance_client.get_symbol_ticker(symbol=symbol.upper())
            current_price = float(ticker['price'])
            actions = get_grid_actions(config, current_price)
            status_result["status"] = "grid_state"
            status_result["details"] = {"current_price": current_price, "potential_actions": actions}
        elif bot_type == "dca":
            # DCA bot needs state (last investment time, etc.)
            # TODO: Fetch actual state from DB or cache based on bot_id
            dca_state = {
                'last_investment_time': None, # Placeholder
                'average_purchase_price': None, # Placeholder
                'highest_price_since_purchase': None, # Placeholder
                'position_active': False # Placeholder
            }
            # Pass db session and bot_id for potential trade recording (simulation)
            # TODO: Update get_dca_actions signature if needed
            actions = get_dca_actions(config, binance_client, dca_state) # Pass db, bot_id if needed
            status_result["status"] = "dca_state"
            status_result["details"] = {"potential_actions": actions}
        else:
            status_result["status"] = "unsupported_type"
            status_result["details"] = {"message": f"Bot type '{bot_type}' not recognized for status check."}

    except Exception as e:
        print(f"Error getting status for bot {bot_id} ({symbol}): {e}")
        # Don't raise HTTPException here, return status indicating error
        status_result["status"] = "error"
        status_result["details"] = {"error_message": str(e)}

    return status_result


# --- Performance Endpoint ---

@router.get(
    "/{bot_id}/performance",
    response_model=Dict[str, Any], # Define a Pydantic model for better structure later
    summary="Get Bot Performance Metrics"
)
def get_bot_performance(
    *,
    db: Session = Depends(get_db),
    bot_id: int = Path(..., title="The ID of the bot to get performance for", ge=1),
    current_user: dict = Depends(get_current_user) # Protected route
):
    """
    Retrieves and calculates performance metrics based on the trade history
    for a specific bot owned by the user.
    """
    user_id_uuid = uuid.UUID(current_user["id"])
    # Verify bot belongs to user first
    db_bot = crud_bot_config.get_bot_config(db, bot_id=bot_id, user_id=user_id_uuid)
    if db_bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot configuration not found")

    # Fetch trade history for the bot
    trades = crud_trade_history.get_trade_history_for_bot(db, bot_id=bot_id, limit=10000) # Get sufficient history

    # Calculate metrics
    performance_metrics = calculate_performance_metrics(trades)

    return performance_metrics
