"""
Database configuration and session management.

What: SQLAlchemy database setup for chat history persistence
Why: Enable persistent storage of user chat conversations
How: SQLAlchemy with async support and connection pooling
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Database URL - using SQLite for simplicity, can be changed to PostgreSQL/MySQL
DATABASE_URL = settings.database_url

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models in this module (not used by chat models which define their own Base)
Base = declarative_base()


async def get_db():
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    try:
        # Import chat models and create all tables for their Base
        from app.models import chat_models as chat_models
        async with engine.begin() as conn:
            await conn.run_sync(chat_models.Base.metadata.create_all)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        raise


async def close_db():
    """Close database connections."""
    await engine.dispose()
    logger.info("✅ Database connections closed")
