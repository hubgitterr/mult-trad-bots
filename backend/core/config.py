import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import List, Union, Optional # Added Optional

# Load .env file from the backend directory
# Adjust the path if your .env file is located elsewhere
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Multiple Trading Bots Backend"
    API_V1_STR: str = "/api/v1"

    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_DB_CONNECTION_STRING: str

    # Binance API Credentials (Live)
    BINANCE_API_KEY: str
    BINANCE_SECRET_KEY: str

    # Binance Testnet (Optional)
    BINANCE_TESTNET_API_KEY: Optional[str] = None
    BINANCE_TESTNET_SECRET_KEY: Optional[str] = None
    # pydantic-settings automatically handles boolean conversion for env vars
    # "true", "1", "yes" -> True; "false", "0", "no" -> False
    BINANCE_USE_TESTNET: bool = False

    # Optional: CORS Origins (example)
    # BACKEND_CORS_ORIGINS: Union[str, List[str]] = '["http://localhost:3000"]'

    class Config:
        case_sensitive = True
        # env_file = ".env" # pydantic-settings can load directly if needed
        # env_file_encoding = 'utf-8'


# Instantiate settings
settings = Settings()

# Example usage: print(settings.SUPABASE_URL)
