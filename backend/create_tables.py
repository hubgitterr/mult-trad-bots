import sys
import os

# Add the backend directory to the Python path to allow absolute imports
# This is necessary because we are running this script directly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import engine, Base
# Import all models from the models package to ensure they are registered with Base
# The __init__.py file in the models directory handles importing individual models
import models # noqa: F401 (flake8 ignore: module imported but unused)

def create_database_tables():
    """Creates all tables defined in the models linked to the Base metadata."""
    print("Attempting to create database tables...")
    try:
        # Ensure all models are imported before calling create_all
        # The 'import models' above should handle this due to models/__init__.py
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully (if they didn't exist already).")
        print("Tables expected: users, bot_configurations, trade_history")
    except Exception as e:
        print(f"An error occurred during table creation: {e}")
        print("Please ensure the database connection string in .env is correct and the database is reachable.")

if __name__ == "__main__":
    # This allows the script to be run directly
    # Make sure the virtual environment is activated before running
    # Example command (run from the 'backend' directory):
    # ../venv/Scripts/python create_tables.py
    create_database_tables()
