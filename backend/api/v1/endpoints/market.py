from fastapi import APIRouter, Query, HTTPException, Depends, Path
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from typing import List, Optional, Dict

# Use absolute imports from 'backend' root
from core.binance_client import get_binance_client
from schemas.market import KlineResponse, KlineDataPoint
# No specific schema needed for ticker response, it's usually a simple dict

router = APIRouter()

@router.get(
    "/klines",
    response_model=KlineResponse,
    summary="Get Historical Kline/Candlestick Data",
    description="Fetches historical kline data for a specific symbol and interval from Binance."
)
async def get_klines(
    symbol: str = Query(..., description="Trading symbol (e.g., BTCUSDT)", example="BTCUSDT"),
    interval: str = Query(..., description="Kline interval (e.g., 1m, 5m, 1h, 1d)", example="1h"),
    limit: Optional[int] = Query(default=500, ge=1, le=1000, description="Number of klines to retrieve (max 1000)"),
    startTime: Optional[int] = Query(default=None, description="Start time in milliseconds"),
    endTime: Optional[int] = Query(default=None, description="End time in milliseconds"),
    client: Client = Depends(get_binance_client) # Dependency injection for Binance client
):
    """
    Retrieves historical kline/candlestick data for a given symbol and interval.
    """
    if not client:
        raise HTTPException(status_code=503, detail="Binance client not available.")

    try:
        # Construct parameters for the API call, excluding None values
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit,
        }
        if startTime:
            params["startTime"] = startTime
        if endTime:
            params["endTime"] = endTime

        klines_data: List[KlineDataPoint] = client.get_klines(**params)

        if not klines_data:
            # Return empty list if no data found, maybe log a warning
            return KlineResponse(symbol=symbol, interval=interval, klines=[])

        # Data is already in the format expected by KlineDataPoint
        return KlineResponse(symbol=symbol, interval=interval, klines=klines_data)

    except BinanceAPIException as e:
        # Handle specific Binance API errors (e.g., invalid symbol)
        raise HTTPException(status_code=400, detail=f"Binance API error: {e.message}")
    except BinanceRequestException as e:
        # Handle request errors (e.g., network issues)
        raise HTTPException(status_code=504, detail=f"Binance request error: {e.message}")
    except Exception as e:
        # Catch any other unexpected errors
        # Log the error for debugging: print(f"Unexpected error fetching klines: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get(
    "/ticker/{symbol}",
    response_model=Dict, # Returns a dictionary, structure defined by Binance
    summary="Get Latest Ticker Price",
    description="Fetches the latest price ticker information for a specific symbol from Binance."
)
async def get_ticker(
    symbol: str = Path(..., description="Trading symbol (e.g., BTCUSDT)", example="BTCUSDT"),
    client: Client = Depends(get_binance_client) # Dependency injection
):
    """
    Retrieves the latest price ticker information for a specific symbol.
    """
    if not client:
        raise HTTPException(status_code=503, detail="Binance client not available.")

    try:
        ticker_info = client.get_symbol_ticker(symbol=symbol.upper())
        if not ticker_info:
             raise HTTPException(status_code=404, detail=f"Ticker information not found for symbol: {symbol}")
        return ticker_info # Returns dict like {'symbol': 'BTCUSDT', 'price': '25000.00'}

    except BinanceAPIException as e:
        # Handle specific Binance API errors (e.g., invalid symbol)
        if 'Invalid symbol' in e.message:
             raise HTTPException(status_code=404, detail=f"Invalid symbol: {symbol}")
        raise HTTPException(status_code=400, detail=f"Binance API error: {e.message}")
    except BinanceRequestException as e:
        # Handle request errors
        raise HTTPException(status_code=504, detail=f"Binance request error: {e.message}")
    except Exception as e:
        # Catch any other unexpected errors
        # Log the error: print(f"Unexpected error fetching ticker for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
