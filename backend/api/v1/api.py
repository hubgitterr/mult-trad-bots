from fastapi import APIRouter

# Use absolute imports from 'backend' root
from api.v1.endpoints import market, bots, websockets

api_router = APIRouter()

# Include routers from endpoint modules
api_router.include_router(market.router, prefix="/market", tags=["Market Data"])
api_router.include_router(bots.router, prefix="/bots", tags=["Bot Management"])
api_router.include_router(websockets.router, tags=["WebSockets"]) # WebSocket router (no prefix needed if path includes it)
# Add other routers here later (e.g., for auth if needed separately)
