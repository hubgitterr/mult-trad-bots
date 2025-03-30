import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta, timezone
from binance.client import Client
from binance.exceptions import BinanceAPIException
from typing import Dict, Any, List, Optional, Literal, TypedDict
from sqlalchemy.orm import Session # Added Session

# Use absolute imports from 'backend' root
from app.crud import crud_trade_history
from schemas.trade_history import TradeHistoryCreate

# Type hint for the actions returned
class DcaAction(TypedDict):
    action: Literal['DCA_BUY', 'SMART_DIP_BUY', 'TRAILING_STOP_SELL', 'HOLD']
    amount: Optional[float] # Amount to buy (in quote currency, e.g., USDT) or None for sell/hold
    price: Optional[float] # Price at which action is triggered (current price)

def should_invest_now(frequency: str, last_investment_time: Optional[datetime]) -> bool:
    """Checks if an investment should be made based on frequency."""
    if last_investment_time is None:
        return True # First investment

    now = datetime.now(timezone.utc)
    # Ensure last_investment_time is timezone-aware (UTC)
    if last_investment_time.tzinfo is None or last_investment_time.tzinfo.utcoffset(last_investment_time) is None:
         # If timezone naive, assume UTC for comparison, but log warning
         print("Warning: last_investment_time is timezone-naive. Assuming UTC.")
         last_investment_time = last_investment_time.replace(tzinfo=timezone.utc)

    delta: Optional[timedelta] = None
    if frequency == 'daily':
        delta = timedelta(days=1)
    elif frequency == 'weekly':
        delta = timedelta(weeks=1)
    elif frequency == 'hourly': # Example additional frequency
        delta = timedelta(hours=1)
    # Add more frequencies as needed (monthly, etc.)

    if delta is None:
        print(f"DCA Bot: Unsupported frequency '{frequency}'")
        return False

    return now >= (last_investment_time + delta)

# Updated signature to accept db and bot_id for trade recording/state updates
def get_dca_actions(config: Dict[str, Any], client: Client, state: Dict[str, Any], db: Optional[Session] = None, bot_id: Optional[int] = None) -> List[DcaAction]:
    """
    Calculates potential DCA actions based on frequency, smart dips, and trailing stops.
    Optionally records simulated trades if db and bot_id are provided.

    Args:
        config: Dictionary containing bot settings like:
            'symbol': Trading symbol (e.g., 'BTCUSDT').
            'investment_amount': Base amount to invest per period (e.g., 100 USDT).
            'frequency': Investment frequency ('daily', 'weekly', 'hourly', etc.).
            'smart_dip_pct': Optional percentage below MA to trigger extra buy (e.g., 5 for 5%).
            'smart_dip_ma_period': Optional MA period for smart dip (e.g., 20).
            'smart_dip_ma_type': Optional MA type ('sma' or 'ema').
            'smart_dip_multiplier': Optional multiplier for investment amount on dip (e.g., 1.5).
            'trailing_stop_pct': Optional percentage for trailing stop-loss (e.g., 10 for 10%).
        client: Initialized Binance client instance.
        state: Dictionary containing the bot's current state like:
             'last_investment_time': datetime of the last investment.
             'average_purchase_price': Average price of current holdings.
             'highest_price_since_purchase': Highest price reached since last buy for trailing stop.
             'position_active': Boolean indicating if currently holding assets bought by this bot.
        db: Optional SQLAlchemy Session for recording trades/state updates.
        bot_id: Optional Bot ID for recording trades/state updates.


    Returns:
        A list of potential actions (DcaAction dictionaries).
    """
    symbol = config.get('symbol', 'BTCUSDT')
    investment_amount = config.get('investment_amount')
    frequency = config.get('frequency')
    smart_dip_pct = config.get('smart_dip_pct')
    smart_dip_ma_period = config.get('smart_dip_ma_period', 20)
    smart_dip_ma_type = config.get('smart_dip_ma_type', 'sma').lower()
    smart_dip_multiplier = config.get('smart_dip_multiplier', 1.0) # Default to no multiplier
    trailing_stop_pct = config.get('trailing_stop_pct')

    # --- State variables (passed in, would normally come from DB/cache) ---
    last_investment_time = state.get('last_investment_time')
    average_purchase_price = state.get('average_purchase_price')
    highest_price_since_purchase = state.get('highest_price_since_purchase')
    position_active = state.get('position_active', False) # Is there an active position to monitor?
    # --- End State ---

    potential_actions: List[DcaAction] = []

    if not investment_amount or not frequency:
        print(f"DCA Bot ({symbol}): Invalid config - missing investment_amount or frequency.")
        return [{'action': 'HOLD', 'amount': None, 'price': None}]

    try:
        # 1. Get Current Price
        ticker = client.get_symbol_ticker(symbol=symbol.upper())
        current_price = float(ticker['price'])

        # --- Helper function to record trades ---
        def record_simulated_trade(action_type: Literal['SIM_BUY', 'SIM_SELL'], amount: Optional[float], price: float):
            if db is not None and bot_id is not None:
                try:
                    # Quantity needs calculation for SELL based on holdings, placeholder for now
                    sim_quantity = (amount / price) if amount and price > 0 and action_type == 'SIM_BUY' else 1.0 # Placeholder quantity
                    trade_data = TradeHistoryCreate(
                        bot_id=bot_id, timestamp=datetime.now(timezone.utc), symbol=symbol.upper(),
                        action=action_type, price=price, quantity=sim_quantity
                    )
                    crud_trade_history.create_trade_history(db=db, trade=trade_data)
                    print(f"DCA Bot ({symbol}): Recorded {action_type} at {price}")
                    # TODO: Update bot state in DB (last_investment_time, avg_price, etc.)
                except Exception as e:
                    print(f"DCA Bot ({symbol}): Failed to record simulated trade: {e}")

        # 2. Check Trailing Stop-Loss (only if holding a position and configured)
        if position_active and trailing_stop_pct and average_purchase_price and highest_price_since_purchase:
            stop_loss_price = highest_price_since_purchase * (1 - (trailing_stop_pct / 100.0))
            if current_price < stop_loss_price:
                print(f"DCA Bot ({symbol}): Trailing Stop triggered! Price={current_price}, Stop={stop_loss_price}")
                action: DcaAction = {'action': 'TRAILING_STOP_SELL', 'amount': None, 'price': current_price}
                potential_actions.append(action)
                record_simulated_trade('SIM_SELL', None, current_price)
                # Important: Reset state after sell (position_active=False, etc.) - not done here
                return potential_actions # Exit early after stop-loss

        # 3. Check Regular DCA Investment Time
        invest_now = should_invest_now(frequency, last_investment_time)
        if invest_now:
            print(f"DCA Bot ({symbol}): Regular investment time triggered.")
            action: DcaAction = {'action': 'DCA_BUY', 'amount': investment_amount, 'price': current_price}
            potential_actions.append(action)
            record_simulated_trade('SIM_BUY', investment_amount, current_price)
            # Important: Update last_investment_time in state after buy - not done here

        # 4. Check Smart Dip (only if configured and *not* doing a regular buy now - adjust logic if needed)
        if not invest_now and smart_dip_pct and smart_dip_ma_period:
            try:
                klines = client.get_klines(symbol=symbol.upper(), interval='1d', limit=smart_dip_ma_period + 5)
                if klines:
                    df = pd.DataFrame(klines, columns=['Open_Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_Time', 'Quote_Asset_Volume', 'Number_of_Trades', 'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume', 'Ignore'])
                    df['Close'] = pd.to_numeric(df['Close'])
                    df.rename(columns={'Close': 'close'}, inplace=True)

                    ma_col = f'{smart_dip_ma_type.upper()}_{smart_dip_ma_period}'
                    if smart_dip_ma_type == 'sma': df.ta.sma(length=smart_dip_ma_period, append=True)
                    elif smart_dip_ma_type == 'ema': df.ta.ema(length=smart_dip_ma_period, append=True)
                    else: ma_col = None

                    if ma_col and ma_col in df.columns:
                        df.dropna(inplace=True)
                        if not df.empty:
                            last_ma = df[ma_col].iloc[-1]
                            dip_threshold_price = last_ma * (1 - (smart_dip_pct / 100.0))

                            if current_price < dip_threshold_price:
                                print(f"DCA Bot ({symbol}): Smart Dip detected! Price={current_price}, MA={last_ma:.2f}, Threshold={dip_threshold_price:.2f}")
                                dip_amount = investment_amount * smart_dip_multiplier
                                action: DcaAction = {'action': 'SMART_DIP_BUY', 'amount': dip_amount, 'price': current_price}
                                potential_actions.append(action)
                                record_simulated_trade('SIM_BUY', dip_amount, current_price)
                                # Important: Update state after buy - not done here
            except Exception as ma_err:
                print(f"DCA Bot ({symbol}): Error calculating MA for smart dip: {ma_err}")


        if not potential_actions:
             potential_actions.append({'action': 'HOLD', 'amount': None, 'price': current_price})

        return potential_actions

    except BinanceAPIException as e:
        print(f"DCA Bot ({symbol}): Binance API error: {e}")
        return [{'action': 'HOLD', 'amount': None, 'price': None}]
    except Exception as e:
        print(f"DCA Bot ({symbol}): Unexpected error: {e}")
        return [{'action': 'HOLD', 'amount': None, 'price': None}]


# Example usage (for testing purposes)
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path=dotenv_path)
    API_KEY = os.getenv("BINANCE_API_KEY")
    API_SECRET = os.getenv("BINANCE_SECRET_KEY")

    if not API_KEY or not API_SECRET:
        print("Error: Binance API Key/Secret not found.")
    else:
        test_client = Client(API_KEY, API_SECRET)
        test_config_dca = {
            'symbol': 'ETHUSDT', 'investment_amount': 50, 'frequency': 'daily',
            'smart_dip_pct': 5, 'smart_dip_ma_period': 20, 'smart_dip_ma_type': 'sma',
            'smart_dip_multiplier': 1.5, 'trailing_stop_pct': 10
        }

        print("\n--- Test Case 1: Regular Investment Time ---")
        test_state_1 = {'last_investment_time': datetime.now(timezone.utc) - timedelta(days=2), 'position_active': False}
        actions1 = get_dca_actions(test_config_dca, test_client, test_state_1)
        print(f"Actions (Regular Time): {actions1}")

        print("\n--- Test Case 2: Potential Dip ---")
        test_state_2 = {'last_investment_time': datetime.now(timezone.utc) - timedelta(hours=5), 'position_active': False}
        actions2 = get_dca_actions(test_config_dca, test_client, test_state_2)
        print(f"Actions (Potential Dip): {actions2}")

        print("\n--- Test Case 3: Trailing Stop ---")
        test_state_3 = {
            'last_investment_time': datetime.now(timezone.utc) - timedelta(days=5),
            'average_purchase_price': 3000, 'highest_price_since_purchase': 3500, 'position_active': True
        }
        actions3 = get_dca_actions(test_config_dca, test_client, test_state_3)
        print(f"Actions (Trailing Stop Check): {actions3}")
