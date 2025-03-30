from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from .config import settings # Import settings from the config module

# Initialize the Binance client using API keys from settings
# Ensure that settings are loaded correctly before this module is imported

binance_client: Client | None = None # Initialize as None

try:
    if settings.BINANCE_USE_TESTNET:
        print("--- Initializing Binance Client for TESTNET ---")
        if not settings.BINANCE_TESTNET_API_KEY or not settings.BINANCE_TESTNET_SECRET_KEY:
            raise ValueError("Testnet enabled, but Testnet API keys are missing in settings.")
        binance_client = Client(
            settings.BINANCE_TESTNET_API_KEY,
            settings.BINANCE_TESTNET_SECRET_KEY,
            testnet=True # Crucial parameter for Testnet
        )
    else:
        print("--- Initializing Binance Client for LIVE ---")
        if not settings.BINANCE_API_KEY or not settings.BINANCE_SECRET_KEY:
             raise ValueError("Live Binance API keys are missing in settings.")
        binance_client = Client(settings.BINANCE_API_KEY, settings.BINANCE_SECRET_KEY)

    # Optional: Test connection (e.g., get server time)
    # server_time = binance_client.get_server_time()
    # print(f"Successfully connected to Binance ({'Testnet' if settings.BINANCE_USE_TESTNET else 'Live'}). Server time: {server_time}")

except ValueError as e:
     print(f"Configuration Error initializing Binance client: {e}")
     binance_client = None # Ensure client is None on config error
except (BinanceAPIException, BinanceRequestException) as e:
    print(f"API/Request Error initializing Binance client: {e}")
    binance_client = None # Ensure client is None on connection error
except Exception as e:
    print(f"An unexpected error occurred during Binance client initialization: {e}")
    binance_client = None # Ensure client is None on other errors

def get_binance_client() -> Client | None:
    """
    Dependency function or simple getter to provide the initialized Binance client.
    Returns None if initialization failed.
    """
    # In a real app, you might want more robust error handling or retries here.
    if binance_client is None:
        print("Warning: Binance client was not initialized successfully or is unavailable.")
    return binance_client

# Example usage (can be called from API endpoints or services):
# client = get_binance_client()
# if client:
#     try:
#         info = client.get_exchange_info()
#         print("Exchange info retrieved successfully.")
#     except Exception as e:
#         print(f"Error fetching data from Binance: {e}")
