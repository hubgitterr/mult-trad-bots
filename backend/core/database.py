from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Use absolute import from 'backend' root
from core.config import settings

# Create the SQLAlchemy engine using the database connection string from settings
# pool_pre_ping=True helps manage connections that might have timed out
engine = create_engine(
    settings.SUPABASE_DB_CONNECTION_STRING,
    pool_pre_ping=True
)

# Create a configured "Session" class
# autocommit=False ensures transactions are handled explicitly
# autoflush=False prevents premature flushing of state
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative class definitions
# Our ORM models will inherit from this class
Base = declarative_base()

# Dependency to get DB session in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

print(f"Database engine created for: {engine.url}") # Optional: Log confirmation
