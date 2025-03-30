import pandas as pd
import pandas_ta as ta
from binance.client import Client
from binance.exceptions import BinanceAPIException
from typing import Dict, Any, Literal, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

# Use absolute imports from 'backend' root
from app.crud import crud_trade_history
from schemas.trade_history import TradeHistoryCreate

# Define possible signals
Signal = Literal['BUY', 'SELL', 'HOLD']

# Updated signature to accept db and bot_id for trade recording
def get_momentum_signal(config: Dict[str, Any], client: Client, db: Optional[Session] = None, bot_id: Optional[int] = None) -> Signal:
    """
    Calculates a trading signal based on momentum indicators (RSI, MACD, MAs).
    Optionally records simulated trades if db and bot_id are provided.

    Args:
        config: Dictionary containing bot settings like:
            'symbol': Trading symbol (e.g., 'BTCUSDT')
            'interval': Kline interval (e.g., '1h')
            'rsi_period': Period for RSI calculation (e.g., 14)
            'rsi_oversold': RSI oversold threshold (e.g., 30)
            'rsi_overbought': RSI overbought threshold (e.g., 70)
            'macd_fast': MACD fast period (e.g., 12)
            'macd_slow': MACD slow period (e.g., 26)
            'macd_signal': MACD signal period (e.g., 9)
            'ma_short_period': Short-term moving average period (e.g., 9)
            'ma_long_period': Long-term moving average period (e.g., 21)
            'kline_limit': Number of klines to fetch (e.g., 100)
        client: Initialized Binance client instance.
        db: Optional SQLAlchemy Session for recording trades.
        bot_id: Optional Bot ID for recording trades.

    Returns:
        Trading signal ('BUY', 'SELL', 'HOLD').
    """
    symbol = config.get('symbol', 'BTCUSDT')
    interval = config.get('interval', '1h')
    limit = config.get('kline_limit', 100) # Need enough data for indicators

    # --- Default Indicator Parameters (should be in config ideally) ---
    rsi_period = config.get('rsi_period', 14)
    rsi_oversold = config.get('rsi_oversold', 30)
    rsi_overbought = config.get('rsi_overbought', 70)
    macd_fast = config.get('macd_fast', 12)
    macd_slow = config.get('macd_slow', 26)
    macd_signal = config.get('macd_signal', 9)
    ma_short_period = config.get('ma_short_period', 9)
    ma_long_period = config.get('ma_long_period', 21)
    # --- End Default Parameters ---

    try:
        # 1. Fetch Kline Data
        klines = client.get_klines(symbol=symbol.upper(), interval=interval, limit=limit)
        if not klines:
            print(f"Momentum Bot: No kline data received for {symbol} {interval}")
            return 'HOLD'

        # 2. Convert to Pandas DataFrame
        df = pd.DataFrame(klines, columns=[
            'Open_Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_Time',
            'Quote_Asset_Volume', 'Number_of_Trades', 'Taker_Buy_Base_Asset_Volume',
            'Taker_Buy_Quote_Asset_Volume', 'Ignore'
        ])
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col])
        df['Open_Time'] = pd.to_datetime(df['Open_Time'], unit='ms')
        df['Close_Time'] = pd.to_datetime(df['Close_Time'], unit='ms')
        df.set_index('Close_Time', inplace=True)

        # 3. Calculate Indicators using pandas_ta
        df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
        df.ta.rsi(length=rsi_period, append=True)
        df.ta.macd(fast=macd_fast, slow=macd_slow, signal=macd_signal, append=True)
        df.ta.sma(length=ma_short_period, append=True)
        df.ta.sma(length=ma_long_period, append=True)

        rsi_col = f'RSI_{rsi_period}'
        macd_col = f'MACD_{macd_fast}_{macd_slow}_{macd_signal}'
        macdh_col = f'MACDh_{macd_fast}_{macd_slow}_{macd_signal}'
        macds_col = f'MACDs_{macd_fast}_{macd_slow}_{macd_signal}'
        sma_short_col = f'SMA_{ma_short_period}'
        sma_long_col = f'SMA_{ma_long_period}'

        required_cols = [rsi_col, macd_col, macdh_col, macds_col, sma_short_col, sma_long_col, 'close']
        if not all(col in df.columns for col in required_cols):
             print(f"Momentum Bot: Could not calculate all required indicators for {symbol}. Columns: {df.columns}")
             return 'HOLD'

        df.dropna(inplace=True)
        if df.empty or len(df) < 2: # Need at least 2 rows for prev/latest comparison
            print(f"Momentum Bot: DataFrame empty or too short after dropping NaNs for {symbol}")
            return 'HOLD'

        # 4. Define Signal Logic
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        ma_cross_bullish = prev[sma_short_col] <= prev[sma_long_col] and latest[sma_short_col] > latest[sma_long_col]
        rsi_buy_ok = latest[rsi_col] < rsi_overbought
        macd_bullish = latest[macd_col] > latest[macds_col] and latest[macdh_col] > 0
        buy_signal = ma_cross_bullish and macd_bullish and rsi_buy_ok

        ma_cross_bearish = prev[sma_short_col] >= prev[sma_long_col] and latest[sma_short_col] < latest[sma_long_col]
        rsi_sell_ok = latest[rsi_col] > rsi_oversold
        macd_bearish = latest[macd_col] < latest[macds_col] and latest[macdh_col] < 0
        sell_signal = ma_cross_bearish and macd_bearish and rsi_sell_ok

        # 5. Determine Final Signal & Record Simulated Trade
        final_signal: Signal = 'HOLD'
        trade_action: Optional[str] = None
        if buy_signal:
            final_signal = 'BUY'
            trade_action = 'SIM_BUY'
        elif sell_signal:
            final_signal = 'SELL'
            trade_action = 'SIM_SELL'

        if trade_action and db is not None and bot_id is not None:
            try:
                current_price = latest['close']
                simulated_quantity = 1.0 # Example quantity
                trade_data = TradeHistoryCreate(
                    bot_id=bot_id,
                    timestamp=datetime.now(timezone.utc),
                    symbol=symbol.upper(),
                    action=trade_action,
                    price=current_price,
                    quantity=simulated_quantity
                )
                crud_trade_history.create_trade_history(db=db, trade=trade_data)
                print(f"Momentum Bot ({symbol}): Recorded {trade_action} at {current_price}")
            except Exception as e:
                print(f"Momentum Bot ({symbol}): Failed to record simulated trade: {e}")

        return final_signal

    except BinanceAPIException as e:
        print(f"Momentum Bot: Binance API error for {symbol}: {e}")
        return 'HOLD'
    except Exception as e:
        print(f"Momentum Bot: Unexpected error for {symbol}: {e}")
        return 'HOLD'

# Example usage (for testing purposes)
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    # Assuming running from 'backend' directory for testing
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # Path relative to this file
    load_dotenv(dotenv_path=dotenv_path)

    API_KEY = os.getenv("BINANCE_API_KEY")
    API_SECRET = os.getenv("BINANCE_SECRET_KEY")
    # Add Testnet keys for testing if needed
    # USE_TESTNET = os.getenv("BINANCE_USE_TESTNET", "false").lower() == "true"
    # if USE_TESTNET:
    #     API_KEY = os.getenv("BINANCE_TESTNET_API_KEY")
    #     API_SECRET = os.getenv("BINANCE_TESTNET_SECRET_KEY")

    if not API_KEY or not API_SECRET:
        print("Error: Binance API Key/Secret not found in environment variables.")
    else:
        # testnet_flag = USE_TESTNET # Pass testnet flag if using test keys
        test_client = Client(API_KEY, API_SECRET) # Add testnet=testnet_flag if needed
        test_config = {
            'symbol': 'BTCUSDT',
            'interval': '1h',
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'ma_short_period': 10,
            'ma_long_period': 20,
            'kline_limit': 100
        }
        # Note: Cannot easily test trade recording here without a DB session
        signal = get_momentum_signal(test_config, test_client)
        print(f"Test Signal for {test_config['symbol']} ({test_config['interval']}): {signal}")
