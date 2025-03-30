from pydantic import BaseModel, Field
from typing import List, Optional, Union, Tuple
from datetime import datetime

# Schema for individual Kline/Candlestick data point (matching python-binance format)
# Example: [open_time, open, high, low, close, volume, close_time, quote_asset_volume, number_of_trades, taker_buy_base_asset_volume, taker_buy_quote_asset_volume, ignore]
KlineDataPoint = List[Union[int, str]]

# Schema for the response payload containing a list of klines
class KlineResponse(BaseModel):
    symbol: str = Field(..., example="BTCUSDT")
    interval: str = Field(..., example="1h")
    klines: List[KlineDataPoint] = Field(..., example=[
        [1678886400000, "25000.00", "25100.50", "24950.00", "25050.75", "1000.50", 1678889999999, "25062500.00", 500, "500.25", "12531250.00", "0"],
        # ... more kline data points
    ])

# Optional: Schema for request query parameters if needed beyond path/basic types
# class KlineRequestParams(BaseModel):
#     symbol: str = Field(..., example="BTCUSDT")
#     interval: str = Field(..., example="1h")
#     limit: Optional[int] = Field(default=500, ge=1, le=1000)
#     startTime: Optional[int] = None # Timestamp in ms
#     endTime: Optional[int] = None   # Timestamp in ms
