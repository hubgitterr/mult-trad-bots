import pandas as pd
from typing import List, Dict, Any

# Use absolute imports from 'backend' root
from models.trade_history import TradeHistory # Import the SQLAlchemy model

def calculate_performance_metrics(trades: List[TradeHistory]) -> Dict[str, Any]:
    """
    Calculates performance metrics from a list of trade history records.

    Args:
        trades: A list of TradeHistory SQLAlchemy objects, ordered chronologically.

    Returns:
        A dictionary containing calculated metrics.
    """
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "average_pnl_per_trade": 0,
            "message": "No trades found for performance calculation."
        }

    # Convert to DataFrame for easier calculation
    trade_data = [{
        "timestamp": trade.timestamp,
        "action": trade.action,
        "price": trade.price,
        "quantity": trade.quantity,
        "symbol": trade.symbol # Needed if calculating per symbol later
    } for trade in trades]
    df = pd.DataFrame(trade_data)

    # --- Basic PnL Calculation (Simplified Example) ---
    # This assumes simple buy/sell pairs and doesn't account for fees,
    # partial fills, multiple open positions, or different assets correctly.
    # A robust calculation needs a proper portfolio simulation approach.

    total_pnl = 0.0
    wins = 0
    losses = 0
    last_buy_price = None
    last_buy_quantity = 0

    # Iterate through trades to calculate simple PnL per buy/sell cycle
    for _, trade in df.iterrows():
        action = trade['action']
        price = trade['price']
        quantity = trade['quantity'] # Assuming quantity is consistent for buy/sell

        if action in ['BUY', 'SIM_BUY']:
            # If already holding, this simple logic doesn't handle averaging down well.
            # For simplicity, we just record the latest buy.
            last_buy_price = price
            last_buy_quantity = quantity # Assuming full position bought/sold each time
        elif action in ['SELL', 'SIM_SELL'] and last_buy_price is not None:
            # Calculate PnL for this cycle (Sell Price - Buy Price) * Quantity
            pnl = (price - last_buy_price) * last_buy_quantity
            total_pnl += pnl
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
            # Reset buy info for the next cycle
            last_buy_price = None
            last_buy_quantity = 0

    total_trades_evaluated = wins + losses # Only counts completed buy/sell cycles
    win_rate = (wins / total_trades_evaluated * 100) if total_trades_evaluated > 0 else 0
    avg_pnl = (total_pnl / total_trades_evaluated) if total_trades_evaluated > 0 else 0

    # --- TODO: Implement More Advanced Metrics ---
    # - Max Drawdown: Requires tracking portfolio value over time.
    # - Sharpe Ratio: Requires risk-free rate and std dev of returns.
    # - Sortino Ratio
    # - Handling of fees, commissions, slippage (in simulation)

    return {
        "total_trades_cycles": total_trades_evaluated,
        "winning_trades": wins,
        "losing_trades": losses,
        "win_rate_pct": round(win_rate, 2),
        "total_pnl": round(total_pnl, 4), # Adjust rounding as needed
        "average_pnl_per_cycle": round(avg_pnl, 4),
        "calculation_notes": "Simplified PnL based on sequential buy/sell cycles. Does not account for fees, partial fills, or complex position management."
    }
