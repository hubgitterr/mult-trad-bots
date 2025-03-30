import uuid
from sqlalchemy import Column, String, DateTime, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# Use absolute import from 'backend' root
from core.database import Base

class User(Base):
    """
    SQLAlchemy model for users.
    Uses Supabase Auth user ID as the primary key.
    """
    __tablename__ = "users"

    # Using UUID to align with Supabase Auth user IDs
    # Note: Supabase Auth handles user creation primarily. This table might store
    # additional app-specific user profile info or serve as a reference.
    # Ensure this ID matches the one from Supabase Auth upon creation.
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    # full_name = Column(String, index=True) # Example additional field
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Define the relationship to BotConfiguration
    # 'back_populates' links this relationship to the 'owner' relationship in BotConfiguration
    bots = relationship("BotConfiguration", back_populates="owner")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
