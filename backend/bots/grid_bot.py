import numpy as np
from binance.client import Client
from binance.exceptions import BinanceAPIException
from typing import Dict, Any, List, Optional, TypedDict, Literal

# Type hint for the actions returned
class GridAction(TypedDict):
    action: Literal['BUY', 'SELL']
    price: float
    grid_level: int # Index of the grid line crossed

def get_grid_actions(config: Dict[str, Any], current_price: float) -> List[GridAction]:
    """
    Calculates potential grid trading actions based on the current price crossing grid levels.
    This version simulates actions based on price crossing levels. A real implementation
    would need to track placed orders and current position.

    Args:
        config: Dictionary containing bot settings like:
            'symbol': Trading symbol (e.g., 'BTCUSDT')
            'upper_limit': Upper price boundary of the grid.
            'lower_limit': Lower price boundary of the grid.
            'num_grids': Number of grid lines (creates num_grids - 1 intervals).
            'investment_per_grid': Amount to invest/trade at each grid level (optional for simulation).
        current_price: The current market price of the symbol.

    Returns:
        A list of potential actions (GridAction dictionaries) to be taken.
        Returns an empty list if no grid lines are crossed or config is invalid.
    """
    symbol = config.get('symbol', 'BTCUSDT')
    upper_limit = config.get('upper_limit')
    lower_limit = config.get('lower_limit')
    num_grids = config.get('num_grids')
    # investment_per_grid = config.get('investment_per_grid') # Not used in this simulation logic

    if not all([isinstance(upper_limit, (int, float)),
                isinstance(lower_limit, (int, float)),
                isinstance(num_grids, int),
                upper_limit > lower_limit,
                num_grids >= 2]):
        print(f"Grid Bot ({symbol}): Invalid configuration provided.")
        return [] # Return empty list for invalid config

    # Calculate grid levels using linear spacing
    # Note: Logarithmic spacing might be better for volatile assets
    grid_levels = np.linspace(lower_limit, upper_limit, num_grids)

    # --- Simulation Logic ---
    # This is a simplified simulation. A real bot needs state:
    # - What orders are currently open?
    # - What is the current position size?
    # - Which grid levels have already been triggered for buys/sells?

    # For this simulation, let's assume we want to:
    # - Place a BUY order if the price drops BELOW a grid level (expecting a bounce back up).
    # - Place a SELL order if the price rises ABOVE a grid level (taking profit).
    # We'll return actions for *every* grid line crossed since the *last check*.
    # A real bot would likely only act on the *first* unfulfilled level crossed.

    potential_actions: List[GridAction] = []

    # Assume 'last_checked_price' was stored somewhere (e.g., in bot state/db)
    # For this example, we'll just check against the current price vs. all levels
    # This means it might generate multiple signals if price jumps across several grids.

    for i, level_price in enumerate(grid_levels):
        # Check for potential BUY signal (price dropped below a level)
        # We typically buy *below* a level, anticipating a rise back to it or the next one.
        # Let's refine: trigger buy if price crosses *down* through a level.
        # This requires knowing the previous price, which we don't have here.
        # Simplified: If current price is below a level, consider it a potential buy zone *if not already bought*.
        if current_price < level_price:
            # In a real bot: Check if a buy order for this level is already placed or filled.
            # If not, place a buy order at 'level_price' or slightly below.
            # For simulation, just note the potential action.
            # Let's assume we buy *at* the level price when crossed downwards.
            # We need previous price to detect the cross, so this simulation is limited.
            # Alternative simulation: If price is below level i, and above level i-1, maybe buy at level i?
            pass # Cannot reliably simulate buy on cross-down without previous price

        # Check for potential SELL signal (price rose above a level)
        # We typically sell *above* a level.
        # Let's refine: trigger sell if price crosses *up* through a level.
        # Simplified: If current price is above a level, consider it a potential sell zone *if holding position bought lower*.
        if current_price > level_price:
            # In a real bot: Check if holding a position bought at a lower level (e.g., level i-1).
            # If yes, and no sell order exists for this level, place sell order at 'level_price' or slightly above.
            # For simulation: Note the potential action. Assume sell *at* the level price.
            # Again, needs previous price for cross detection.
            pass # Cannot reliably simulate sell on cross-up without previous price

    # --- Revised Simulation (Simpler: Action based on current price relative to grid) ---
    # This is less realistic but works without storing previous state.
    # Find the closest grid level *below* the current price.
    lower_grids = grid_levels[grid_levels < current_price]
    closest_lower_level_index = np.argmax(lower_grids) if len(lower_grids) > 0 else -1

    # Find the closest grid level *above* the current price.
    upper_grids = grid_levels[grid_levels > current_price]
    closest_upper_level_index = np.argmin(upper_grids) + len(lower_grids) if len(upper_grids) > 0 else -1 # Adjust index

    # Potential Buy: If price is near the bottom or just crossed a level downwards (hard to tell without prev price)
    # Let's assume a buy signal if price is below the second level (index 1)
    if current_price < grid_levels[1]: # Very basic buy signal
         potential_actions.append({'action': 'BUY', 'price': grid_levels[0], 'grid_level': 0}) # Simulate buying at lowest level

    # Potential Sell: If price is near the top or just crossed a level upwards
    # Let's assume a sell signal if price is above the second-to-last level
    if current_price > grid_levels[-2]: # Very basic sell signal
        potential_actions.append({'action': 'SELL', 'price': grid_levels[-1], 'grid_level': num_grids - 1}) # Simulate selling at highest level


    # A more stateful simulation would look like:
    # 1. Get current open orders from DB/state for this bot.
    # 2. Get current position size.
    # 3. Compare current_price to grid_levels.
    # 4. If price drops below level `i` and no buy order exists at `i`, create BUY action.
    # 5. If price rises above level `j` and position exists from level `j-1` and no sell order exists at `j`, create SELL action.

    print(f"Grid Bot ({symbol}): Price={current_price}, Levels={grid_levels.round(2)}, Actions={potential_actions}")
    return potential_actions


# Example usage (for testing purposes)
if __name__ == '__main__':
    test_config_grid = {
        'symbol': 'BTCUSDT',
        'upper_limit': 52000,
        'lower_limit': 48000,
        'num_grids': 5, # Creates 4 intervals: 48k, 49k, 50k, 51k, 52k
        'investment_per_grid': 100
    }
    test_price_1 = 47500.0
    test_price_2 = 49500.0
    test_price_3 = 51500.0

    actions1 = get_grid_actions(test_config_grid, test_price_1)
    print(f"Actions for price {test_price_1}: {actions1}")

    actions2 = get_grid_actions(test_config_grid, test_price_2)
    print(f"Actions for price {test_price_2}: {actions2}")

    actions3 = get_grid_actions(test_config_grid, test_price_3)
    print(f"Actions for price {test_price_3}: {actions3}")
