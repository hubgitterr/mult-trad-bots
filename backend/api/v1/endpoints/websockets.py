import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Path, HTTPException
from typing import List, Dict, Set
from binance import AsyncClient, BinanceSocketManager

# Use absolute imports from 'backend' root
from core.config import settings

router = APIRouter()

# --- Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        symbol_upper = symbol.upper()
        if symbol_upper not in self.active_connections:
            self.active_connections[symbol_upper] = set()
        self.active_connections[symbol_upper].add(websocket)
        print(f"WebSocket connected: {websocket.client.host}:{websocket.client.port} for {symbol_upper}")
        print(f"Active connections for {symbol_upper}: {len(self.active_connections[symbol_upper])}")

    def disconnect(self, websocket: WebSocket, symbol: str):
        symbol_upper = symbol.upper()
        if symbol_upper in self.active_connections:
            try:
                self.active_connections[symbol_upper].remove(websocket)
                print(f"WebSocket disconnected: {websocket.client.host}:{websocket.client.port} from {symbol_upper}")
                if not self.active_connections[symbol_upper]:
                    del self.active_connections[symbol_upper]
                    print(f"No active connections left for {symbol_upper}. Removed.")
                else:
                    print(f"Active connections remaining for {symbol_upper}: {len(self.active_connections[symbol_upper])}")
            except KeyError:
                 print(f"WebSocket already removed for {symbol_upper}.") # Handle case where disconnect might be called twice

    async def broadcast_to_symbol(self, message: str, symbol: str):
        symbol_upper = symbol.upper()
        if symbol_upper in self.active_connections:
            # Use list comprehension for potentially disconnected clients during broadcast
            disconnected_clients = set()
            tasks = []
            for conn in self.active_connections[symbol_upper]:
                try:
                    tasks.append(conn.send_text(message))
                except Exception as e: # Catch errors during send attempt (e.g., connection closed)
                    print(f"Error sending to client {conn.client.host}:{conn.client.port} for {symbol_upper}: {e}")
                    disconnected_clients.add(conn)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True) # Allow tasks to complete, capture errors

            # Clean up clients that failed during broadcast
            for client in disconnected_clients:
                 self.disconnect(client, symbol_upper)


manager = ConnectionManager()

# --- Binance WebSocket Task ---
binance_socket_tasks: Dict[str, asyncio.Task] = {}
async_binance_client: AsyncClient | None = None # Global async client instance

async def get_async_binance_client() -> AsyncClient:
    """Creates or returns the global async Binance client."""
    global async_binance_client
    if async_binance_client is None:
        api_key = settings.BINANCE_TESTNET_API_KEY if settings.BINANCE_USE_TESTNET else settings.BINANCE_API_KEY
        api_secret = settings.BINANCE_TESTNET_SECRET_KEY if settings.BINANCE_USE_TESTNET else settings.BINANCE_SECRET_KEY
        use_testnet = settings.BINANCE_USE_TESTNET

        if not api_key or not api_secret:
            raise ValueError("Appropriate Binance API keys are missing in settings for AsyncClient.")

        print(f"--- Initializing Binance AsyncClient ({'Testnet' if use_testnet else 'Live'}) ---")
        async_binance_client = await AsyncClient.create(api_key, api_secret, testnet=use_testnet)
    return async_binance_client

async def close_async_binance_client():
    """Closes the global async Binance client connection."""
    global async_binance_client
    if async_binance_client:
        print("--- Closing Binance AsyncClient Connection ---")
        await async_binance_client.close_connection()
        async_binance_client = None


async def binance_websocket_listener(symbol: str):
    """Connects to Binance WebSocket and forwards messages."""
    symbol_upper = symbol.upper()
    print(f"Starting Binance WebSocket listener for {symbol_upper}...")
    client = None # Define client in the outer scope
    try:
        client = await get_async_binance_client()
        bsm = BinanceSocketManager(client)
        stream_name = f"{symbol_upper.lower()}@ticker"

        async with bsm.symbol_ticker_socket(symbol=symbol_upper) as stream:
            while True:
                try:
                    msg = await stream.recv()
                    if msg and 'stream' in msg:
                        data_to_send = json.dumps(msg['data'])
                        await manager.broadcast_to_symbol(data_to_send, symbol_upper)
                    else:
                        pass # Ignore non-stream messages
                except asyncio.CancelledError:
                     print(f"Binance listener task for {symbol_upper} cancelled.")
                     break # Exit loop if task is cancelled
                except Exception as e:
                    print(f"Error receiving/processing message from Binance for {symbol_upper}: {e}")
                    await asyncio.sleep(5) # Wait before continuing loop

    except ValueError as e: # Catch config errors from get_async_binance_client
         print(f"Configuration error starting listener for {symbol_upper}: {e}")
    except Exception as e:
        print(f"Error establishing Binance WebSocket connection for {symbol_upper}: {e}")
    finally:
        print(f"Binance WebSocket listener for {symbol_upper} stopped.")
        # Don't close the global client here, manage it via lifespan
        if symbol_upper in binance_socket_tasks:
            del binance_socket_tasks[symbol_upper]


# --- FastAPI WebSocket Endpoint ---
@router.websocket("/ws/market-updates/{symbol}")
async def websocket_endpoint(
    websocket: WebSocket,
    symbol: str = Path(...)
):
    symbol_upper = symbol.upper()
    await manager.connect(websocket, symbol_upper)

    # Start Binance listener task for this symbol if not already running
    if symbol_upper not in binance_socket_tasks or binance_socket_tasks[symbol_upper].done():
        print(f"Creating new Binance listener task for {symbol_upper}")
        try:
            # Ensure async client is ready before starting listener
            await get_async_binance_client()
            task = asyncio.create_task(binance_websocket_listener(symbol_upper))
            binance_socket_tasks[symbol_upper] = task
        except ValueError as e:
             print(f"Cannot start listener for {symbol_upper}: {e}")
             await websocket.close(code=1011, reason=str(e)) # Close connection with error
             manager.disconnect(websocket, symbol_upper)
             return # Stop processing this connection
        except Exception as e:
             print(f"Unexpected error getting async client for {symbol_upper}: {e}")
             await websocket.close(code=1011, reason="Internal server error")
             manager.disconnect(websocket, symbol_upper)
             return
    else:
         print(f"Binance listener task for {symbol_upper} already running.")

    try:
        while True:
            # Keep connection alive by waiting for potential messages (or ping/pong)
            # If client sends data, it will break the sleep
            await websocket.receive_text() # Example: wait for client message
            # Or simply sleep if no client messages are expected:
            # await asyncio.sleep(3600) # Sleep for a long time
    except WebSocketDisconnect:
        print(f"Client disconnected normally for {symbol_upper}.")
        manager.disconnect(websocket, symbol_upper)
    except Exception as e:
        print(f"Unexpected error in WebSocket endpoint for {symbol_upper}: {e}")
        manager.disconnect(websocket, symbol_upper) # Ensure disconnect on error
    finally:
         # Optional: Check if task should be cancelled if no connections remain
         if symbol_upper not in manager.active_connections and symbol_upper in binance_socket_tasks:
             if not binance_socket_tasks[symbol_upper].done():
                 print(f"Last client disconnected for {symbol_upper}. Cancelling listener task.")
                 binance_socket_tasks[symbol_upper].cancel()
             # Remove reference even if already done/cancelled
             del binance_socket_tasks[symbol_upper]

# --- Add Lifespan Management for Async Client ---
# This should be added to main.py's lifespan context manager

# Example (to be merged into main.py's lifespan):
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     logger.info("Starting up...")
#     await get_async_binance_client() # Initialize global client on startup
#     scheduler.add_job(...)
#     scheduler.start()
#     yield
#     # Shutdown
#     logger.info("Shutting down...")
#     scheduler.shutdown()
#     await close_async_binance_client() # Close global client on shutdown
#     logger.info("Shutdown complete.")
