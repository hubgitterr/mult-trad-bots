from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException, BinanceOrderMinAmountException
from typing import Dict, Any, Literal, Optional
import math

# Use absolute imports from 'backend' root
from core.binance_client import get_binance_client
from app.crud import crud_trade_history
from schemas.trade_history import TradeHistoryCreate
from sqlalchemy.orm import Session
from datetime import datetime, timezone

OrderSide = Literal['BUY', 'SELL']
OrderType = Literal['MARKET', 'LIMIT'] # Add other types if needed

# --- Helper Function to Get Symbol Info (Precision, Min Notional etc.) ---
# Cache this info to avoid repeated API calls
symbol_info_cache: Dict[str, Dict[str, Any]] = {}

def get_symbol_info(client: Client, symbol: str) -> Optional[Dict[str, Any]]:
    """Fetches and caches symbol information from Binance."""
    symbol_upper = symbol.upper()
    if symbol_upper in symbol_info_cache:
        return symbol_info_cache[symbol_upper]
    try:
        info = client.get_symbol_info(symbol_upper)
        if info:
            symbol_info_cache[symbol_upper] = info
            return info
        else:
            print(f"TradeExecutor: Could not find info for symbol {symbol_upper}")
            return None
    except BinanceAPIException as e:
        print(f"TradeExecutor: API Error fetching info for {symbol_upper}: {e}")
        return None

def adjust_quantity_to_step_size(quantity: float, step_size: str) -> float:
    """Adjusts quantity to match the symbol's step size."""
    step = float(step_size)
    # Calculate precision from step size (e.g., 0.001 -> 3 decimal places)
    precision = int(round(-math.log(step, 10), 0)) if step > 0 else 0
    factor = 10 ** precision
    return math.floor(quantity * factor) / factor

def adjust_price_to_tick_size(price: float, tick_size: str) -> float:
    """Adjusts price to match the symbol's tick size (for LIMIT orders)."""
    tick = float(tick_size)
    precision = int(round(-math.log(tick, 10), 0)) if tick > 0 else 0
    factor = 10 ** precision
    # For limit orders, rounding might depend on buy/sell, but floor is safer generally
    return math.floor(price * factor) / factor


# --- Main Execution Function ---
def execute_trade(
    db: Session, # Database session for recording
    bot_id: int,
    symbol: str,
    side: OrderSide,
    order_type: OrderType = 'MARKET', # Corrected: Use string literal for default
    quantity: Optional[float] = None, # Base asset quantity (e.g., BTC amount)
    quote_order_qty: Optional[float] = None, # Quote asset quantity (e.g., USDT amount for MARKET buys)
    price: Optional[float] = None, # Required for LIMIT orders
    client: Optional[Client] = None # Allow passing client or get default
) -> Optional[Dict[str, Any]]:
    """
    Places a trade order on Binance (or Testnet) and records it.

    Args:
        db: SQLAlchemy Session.
        bot_id: ID of the bot initiating the trade.
        symbol: Trading symbol (e.g., BTCUSDT).
        side: 'BUY' or 'SELL'.
        order_type: 'MARKET' or 'LIMIT'.
        quantity: Amount of base asset (required for SELL MARKET/LIMIT, BUY LIMIT).
        quote_order_qty: Amount of quote asset (optional for BUY MARKET).
        price: Price for LIMIT orders.
        client: Optional Binance client instance.

    Returns:
        The order response dictionary from Binance if successful, None otherwise.
    """
    if client is None:
        client = get_binance_client()

    if not client:
        print("TradeExecutor: Binance client not available.")
        return None

    symbol_upper = symbol.upper()
    print(f"TradeExecutor: Attempting {side} {order_type} for {symbol_upper} (Bot ID: {bot_id})")

    # --- Parameter Validation & Adjustment ---
    symbol_info = get_symbol_info(client, symbol_upper)
    if not symbol_info:
        print(f"TradeExecutor: Cannot execute trade, failed to get info for {symbol_upper}")
        return None

    # Find filters for precision and minimums
    lot_size_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
    price_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
    min_notional_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'MIN_NOTIONAL' or f['filterType'] == 'NOTIONAL'), None) # NOTIONAL is for MARKET orders sometimes

    step_size = lot_size_filter['stepSize'] if lot_size_filter else None
    tick_size = price_filter['tickSize'] if price_filter else None
    min_notional = float(min_notional_filter['minNotional']) if min_notional_filter else 5.0 # Default to 5 USDT if not found

    order_params: Dict[str, Any] = {
        "symbol": symbol_upper,
        "side": side,
        "type": order_type,
    }

    # Adjust quantity and add to params if provided
    if quantity is not None:
        if step_size:
            adjusted_quantity = adjust_quantity_to_step_size(quantity, step_size)
            if adjusted_quantity <= 0:
                 print(f"TradeExecutor: Adjusted quantity is zero or less ({adjusted_quantity}) for {symbol_upper}. Original: {quantity}")
                 return None
            order_params["quantity"] = adjusted_quantity
            print(f"TradeExecutor: Original quantity {quantity}, adjusted to {adjusted_quantity} for {symbol_upper}")
        else:
            order_params["quantity"] = quantity # Use original if no step size info
    elif side == 'BUY' and order_type == 'MARKET' and quote_order_qty is not None:
         order_params["quoteOrderQty"] = quote_order_qty # Use quote qty for market buys
    else:
        # Quantity is generally required otherwise
        print(f"TradeExecutor: Missing required quantity/quoteOrderQty for {side} {order_type} {symbol_upper}")
        return None

    # Add price for LIMIT orders
    if order_type == 'LIMIT': # Use string literal for comparison
        if price is None:
            print(f"TradeExecutor: Price is required for LIMIT order on {symbol_upper}")
            return None
        if tick_size:
             adjusted_price = adjust_price_to_tick_size(price, tick_size)
             order_params["price"] = f"{adjusted_price:.{len(tick_size.split('.')[-1])}f}" # Format to correct precision
             order_params["timeInForce"] = "GTC" # Good Till Cancelled
             print(f"TradeExecutor: Original price {price}, adjusted to {order_params['price']} for {symbol_upper}")
        else:
             order_params["price"] = str(price)
             order_params["timeInForce"] = "GTC"


    # --- Minimum Notional Check (Approximate for MARKET) ---
    # For MARKET BUY using quoteOrderQty, it should be >= minNotional
    # For others, calculate notional = price * quantity
    # This requires fetching current price for MARKET SELL or using limit price
    # We'll skip the check for MARKET SELL for simplicity here, but it's important
    current_order_price = price if order_type == 'LIMIT' else None
    if not current_order_price and order_type != 'MARKET': # Need price for check unless market buy with quote qty
         try:
             ticker = client.get_symbol_ticker(symbol=symbol_upper)
             current_order_price = float(ticker['price'])
         except Exception:
              print(f"TradeExecutor: Could not fetch current price for notional check on {symbol_upper}")
              # Proceed cautiously or return None? For now, proceed.

    notional_value = 0
    if "quoteOrderQty" in order_params:
        notional_value = order_params["quoteOrderQty"]
    elif "quantity" in order_params and current_order_price:
        notional_value = order_params["quantity"] * current_order_price

    if notional_value > 0 and notional_value < min_notional:
         print(f"TradeExecutor: Order notional value ({notional_value:.4f}) is below minimum ({min_notional}) for {symbol_upper}. Order rejected.")
         return None


    # --- Place Order ---
    try:
        print(f"TradeExecutor: Placing order with params: {order_params}")
        # Use create_test_order for Testnet, create_order for live
        # We need a way to configure this (e.g., via settings or client init)
        # Assuming client is configured for the correct environment (Live/Testnet)
        # order = client.create_test_order(**order_params) # Use for test orders that don't execute
        order = client.create_order(**order_params) # Use for actual execution
        print(f"TradeExecutor: Order placed successfully for {symbol_upper}. Response: {order}")

        # --- Record Actual Trade ---
        # Extract details from the order response (structure varies slightly)
        trade_price = float(order.get('price', 0.0))
        trade_quantity = float(order.get('executedQty', 0.0))
        order_status = order.get('status')

        # If MARKET order, calculate average fill price if available
        if order_type == 'MARKET' and order_status == 'FILLED' and 'fills' in order and order['fills']:
            total_cost = sum(float(f['price']) * float(f['qty']) for f in order['fills'])
            total_qty = sum(float(f['qty']) for f in order['fills'])
            trade_price = total_cost / total_qty if total_qty > 0 else 0.0
            trade_quantity = total_qty
        elif order_type == 'LIMIT':
             trade_price = float(order.get('price')) # Use the limit price for recording LIMIT orders initially

        if trade_quantity > 0: # Only record if something was executed
            trade_data = TradeHistoryCreate(
                bot_id=bot_id,
                timestamp=datetime.now(timezone.utc),
                symbol=symbol_upper,
                action=side, # Record actual BUY/SELL
                price=trade_price,
                quantity=trade_quantity
                # TODO: Add order ID, status, fees from 'order' response
            )
            crud_trade_history.create_trade_history(db=db, trade=trade_data)
            print(f"TradeExecutor: Recorded actual {side} trade for {symbol_upper} in history.")
        else:
             print(f"TradeExecutor: Order for {symbol_upper} placed but not filled (Qty: {trade_quantity}). Status: {order_status}")


        return order # Return the full order response

    except BinanceOrderMinAmountException as e:
         print(f"TradeExecutor: Order quantity error for {symbol_upper}: {e}")
         # Log details: print(f"Params: {order_params}")
    except BinanceOrderException as e:
        print(f"TradeExecutor: Binance order error for {symbol_upper}: {e}")
        # Log details: print(f"Params: {order_params}")
    except BinanceAPIException as e:
        print(f"TradeExecutor: Binance API error placing order for {symbol_upper}: {e}")
    except Exception as e:
        print(f"TradeExecutor: Unexpected error placing order for {symbol_upper}: {e}")

    return None # Return None if order placement failed
