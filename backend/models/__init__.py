# Import all models here to ensure they are registered with SQLAlchemy's Base
from .user import User
from .bot_configuration import BotConfiguration
from .trade_history import TradeHistory

# Optional: Define __all__ for explicit exports if needed elsewhere
# __all__ = ["User", "BotConfiguration", "TradeHistory"]
