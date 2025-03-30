# This file should be placed in /api/index.py for Vercel deployment
# All other backend code (core, app, bots, etc.) should be moved under /api/ as well.
# Imports are adjusted relative to the /api directory.

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

# Adjusted imports relative to the 'api' directory
from core.config import settings
from api.v1.api import api_router # Assuming v1 router is in api/api/v1/api.py
from core.database import SessionLocal, get_db
from core.binance_client import get_binance_client, Client
from app.crud import crud_bot_config
from bots.momentum_bot import get_momentum_signal
from bots.grid_bot import get_grid_actions
from bots.dca_bot import get_dca_actions
from core.trade_executor import execute_trade
from app.crud.crud_bot_config import get_active_bot_configs
from api.v1.endpoints.websockets import get_async_binance_client, close_async_binance_client

# --- Scheduler Setup ---
scheduler = AsyncIOScheduler()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Bot Execution Job ---
async def run_active_bots_job():
    """Scheduled job to check and potentially execute trades for active bots."""
    logger.info("Scheduler running run_active_bots_job...")
    db: Session = SessionLocal()
    binance_client = get_binance_client()

    if not binance_client:
        logger.error("run_active_bots_job: Binance client not available. Skipping run.")
        db.close()
        return

    try:
        if not hasattr(crud_bot_config, 'get_active_bot_configs'):
             logger.error("run_active_bots_job: crud_bot_config.get_active_bot_configs function not found. Skipping run.")
             db.close()
             return

        active_bots = crud_bot_config.get_active_bot_configs(db)
        logger.info(f"Found {len(active_bots)} active bots to check.")

        for bot in active_bots:
            logger.info(f"Checking bot ID: {bot.id}, Type: {bot.bot_type}, Symbol: {bot.settings.get('symbol')}")
            config = bot.settings
            symbol = config.get('symbol', 'UNKNOWN')
            signal = None
            action_details = None

            try:
                if bot.bot_type == "momentum":
                    signal = get_momentum_signal(config, binance_client)
                    logger.info(f"Bot {bot.id} ({symbol}) Momentum Signal: {signal}")
                elif bot.bot_type == "grid":
                    ticker = binance_client.get_symbol_ticker(symbol=symbol.upper())
                    current_price = float(ticker['price'])
                    action_details = get_grid_actions(config, current_price)
                    logger.info(f"Bot {bot.id} ({symbol}) Grid Actions: {action_details}")
                elif bot.bot_type == "dca":
                    dca_state = { 'last_investment_time': None, 'average_purchase_price': None, 'highest_price_since_purchase': None, 'position_active': False }
                    action_details = get_dca_actions(config, binance_client, dca_state)
                    logger.info(f"Bot {bot.id} ({symbol}) DCA Actions: {action_details}")

                if bot.bot_type == "momentum" and signal in ['BUY', 'SELL']:
                    trade_quantity = 0.001
                    logger.warning(f"Executing {signal} for Bot {bot.id} ({symbol}) - Qty: {trade_quantity} - USING PLACEHOLDER LOGIC")
                    quote_qty = None
                    if signal == 'BUY':
                         quote_qty = 10.0
                         trade_quantity = None
                    order_result = execute_trade(
                        db=db, bot_id=bot.id, symbol=symbol, side=signal,
                        order_type='MARKET', quantity=trade_quantity, quote_order_qty=quote_qty
                    )
                    if order_result:
                        logger.info(f"Trade executed successfully for Bot {bot.id}. Order: {order_result.get('orderId')}")
                    else:
                        logger.error(f"Trade execution failed for Bot {bot.id}.")

            except Exception as bot_err:
                logger.error(f"Error processing bot ID {bot.id} ({symbol}): {bot_err}", exc_info=True)

    except Exception as e:
        logger.error(f"Error in run_active_bots_job: {e}", exc_info=True)
    finally:
        db.close()

# --- FastAPI Lifespan Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    try:
        await get_async_binance_client()
        logger.info("Async Binance client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize async Binance client: {e}")

    logger.info("Starting up scheduler...")
    scheduler.add_job(run_active_bots_job, IntervalTrigger(minutes=1), id="run_active_bots_job", replace_existing=True, misfire_grace_time=30)
    scheduler.start()
    logger.info("Scheduler started.")
    yield
    logger.info("Shutting down application...")
    logger.info("Shutting down scheduler...")
    scheduler.shutdown()
    logger.info("Scheduler shut down.")
    await close_async_binance_client()
    logger.info("Async Binance client closed.")
    logger.info("Shutdown complete.")

# --- Create FastAPI App ---
# Vercel expects the FastAPI instance to be named 'app'
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json", # Adjust path if needed after rewrite
    lifespan=lifespan
)

# --- Root Endpoint (Optional for API) ---
# Vercel might not serve this root directly depending on rewrites
# @app.get("/")
# async def read_api_root():
#     return {"message": "API Root"}

# --- Include API Router ---
# The prefix here might interact with Vercel rewrites.
# Often, the rewrite handles the /api/v1 part.
# Let's include it without the prefix initially, assuming rewrites handle it.
# app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router) # Mount the v1 routes directly

# --- Optional CORS Middleware ---
# Make sure this is configured correctly for your Vercel frontend URL
from fastapi.middleware.cors import CORSMiddleware
# Example: Allow all origins for simplicity, restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Or specify frontend domain: settings.FRONTEND_URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
