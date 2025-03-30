import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

# Use absolute imports for modules relative to the 'backend' directory
# when running main.py as the entry point.
from core.config import settings
from api.v1.api import api_router
from core.database import SessionLocal, get_db
from core.binance_client import get_binance_client, Client
from app.crud import crud_bot_config
from bots.momentum_bot import get_momentum_signal
from bots.grid_bot import get_grid_actions
from bots.dca_bot import get_dca_actions
from core.trade_executor import execute_trade
from app.crud.crud_bot_config import get_active_bot_configs
# This import needs to be absolute from 'backend' as well
from api.v1.endpoints.websockets import get_async_binance_client, close_async_binance_client

# --- Scheduler Setup ---
scheduler = AsyncIOScheduler()

# Configure logging for scheduler and app
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Bot Execution Job ---
async def run_active_bots_job():
    """Scheduled job to check and potentially execute trades for active bots."""
    logger.info("Scheduler running run_active_bots_job...")
    db: Session = SessionLocal() # Create a new session for this job run
    binance_client = get_binance_client() # Get the shared client instance

    if not binance_client:
        logger.error("run_active_bots_job: Binance client not available. Skipping run.")
        db.close()
        return

    try:
        # Ensure the function exists before calling
        if not hasattr(crud_bot_config, 'get_active_bot_configs'):
             logger.error("run_active_bots_job: crud_bot_config.get_active_bot_configs function not found. Skipping run.")
             db.close()
             return

        active_bots = crud_bot_config.get_active_bot_configs(db) # Fetch active bots
        logger.info(f"Found {len(active_bots)} active bots to check.")

        for bot in active_bots:
            logger.info(f"Checking bot ID: {bot.id}, Type: {bot.bot_type}, Symbol: {bot.settings.get('symbol')}")
            config = bot.settings
            symbol = config.get('symbol', 'UNKNOWN')
            signal = None
            action_details = None # For grid/dca potential actions

            try:
                # --- Get Signal/Action ---
                if bot.bot_type == "momentum":
                    # TODO: Pass db and bot_id if momentum bot needs to record trades
                    # Modify get_momentum_signal signature if it needs db/bot_id
                    signal = get_momentum_signal(config, binance_client) # Pass db, bot.id if needed
                    logger.info(f"Bot {bot.id} ({symbol}) Momentum Signal: {signal}")
                elif bot.bot_type == "grid":
                    ticker = binance_client.get_symbol_ticker(symbol=symbol.upper())
                    current_price = float(ticker['price'])
                    # TODO: Grid bot needs state (open orders) for real execution
                    action_details = get_grid_actions(config, current_price) # Returns list of potential actions
                    logger.info(f"Bot {bot.id} ({symbol}) Grid Actions: {action_details}")
                    # TODO: Translate grid actions into actual BUY/SELL signals/orders
                elif bot.bot_type == "dca":
                     # TODO: Fetch actual state from DB for bot_id
                    dca_state = { 'last_investment_time': None, 'average_purchase_price': None, 'highest_price_since_purchase': None, 'position_active': False }
                    # TODO: Pass db and bot_id if dca bot needs to record trades/update state
                    # Modify get_dca_actions signature if it needs db/bot_id
                    action_details = get_dca_actions(config, binance_client, dca_state) # Pass db, bot.id if needed
                    logger.info(f"Bot {bot.id} ({symbol}) DCA Actions: {action_details}")
                    # TODO: Translate DCA actions into actual BUY/SELL signals/orders

                # --- Execute Trade (Example for Momentum) ---
                # WARNING: Real execution logic needs careful implementation! Basic placeholder.
                if bot.bot_type == "momentum" and signal in ['BUY', 'SELL']:
                    trade_quantity = 0.001 # Example fixed quantity (BTC) - VERY DANGEROUS
                    logger.warning(f"Executing {signal} for Bot {bot.id} ({symbol}) - Qty: {trade_quantity} - USING PLACEHOLDER LOGIC")
                    quote_qty = None
                    if signal == 'BUY':
                         quote_qty = 10.0 # Example: Buy $10 worth
                         trade_quantity = None

                    order_result = execute_trade(
                        db=db, bot_id=bot.id, symbol=symbol, side=signal,
                        order_type='MARKET', quantity=trade_quantity, quote_order_qty=quote_qty
                    )
                    if order_result:
                        logger.info(f"Trade executed successfully for Bot {bot.id}. Order: {order_result.get('orderId')}")
                        # TODO: Update bot state (e.g., position size, average price) in DB
                    else:
                        logger.error(f"Trade execution failed for Bot {bot.id}.")

                # TODO: Add execution logic for Grid and DCA based on their actions

            except Exception as bot_err:
                logger.error(f"Error processing bot ID {bot.id} ({symbol}): {bot_err}", exc_info=True)

    except Exception as e:
        logger.error(f"Error in run_active_bots_job: {e}", exc_info=True)
    finally:
        db.close() # Ensure session is closed


# --- FastAPI Lifespan Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    try:
        await get_async_binance_client() # Initialize global async client on startup
        logger.info("Async Binance client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize async Binance client: {e}")
        # Decide if app should fail to start or continue without WS client

    logger.info("Starting up scheduler...")
    # Add the job to run every minute (adjust interval as needed)
    scheduler.add_job(run_active_bots_job, IntervalTrigger(minutes=1), id="run_active_bots_job", replace_existing=True, misfire_grace_time=30)
    scheduler.start()
    logger.info("Scheduler started.")
    yield
    # Shutdown
    logger.info("Shutting down application...")
    logger.info("Shutting down scheduler...")
    scheduler.shutdown()
    logger.info("Scheduler shut down.")
    await close_async_binance_client() # Close global async client on shutdown
    logger.info("Async Binance client closed.")
    logger.info("Shutdown complete.")


# --- Create FastAPI App ---
# Initialize app with lifespan manager first
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan # Add lifespan context manager
)

# --- Root Endpoint ---
@app.get("/")
async def read_root():
    """Root endpoint to check if the backend is online."""
    scheduler_running = scheduler.running if scheduler else False
    return {"message": "Backend Online - Welcome!", "scheduler_running": scheduler_running}

# --- Include API Router ---
app.include_router(api_router, prefix=settings.API_V1_STR)


# --- Optional CORS Middleware ---
# from fastapi.middleware.cors import CORSMiddleware
# if settings.BACKEND_CORS_ORIGINS:
#     allow_origins = [str(origin).strip() for origin in settings.BACKEND_CORS_ORIGINS.split(",")]
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=allow_origins,
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )

# --- Example Run Command ---
# cd multiple-trading-bots/backend
# ../venv/Scripts/uvicorn main:app --reload --host 0.0.0.0 --port 8000
