"""
Database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from .config import settings


# Convert database URL for async
DATABASE_URL = settings.DATABASE_URL

# Handle SQLite vs PostgreSQL
if DATABASE_URL.startswith("sqlite:///"):
    # SQLite: use aiosqlite for async
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    # SQLite needs check_same_thread=False for async
    sync_engine = create_engine(
        DATABASE_URL,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=settings.DEBUG,
    )
elif DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    sync_engine = create_engine(
        DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )
    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )
else:
    ASYNC_DATABASE_URL = DATABASE_URL
    sync_engine = create_engine(DATABASE_URL, echo=settings.DEBUG)
    async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=settings.DEBUG)

# Session factories
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db():
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db():
    """Get sync database session for scripts"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """Create all tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await async_engine.dispose()
