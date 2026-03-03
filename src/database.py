"""
Database connection and session management
"""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from .config import settings


# Convert database URL for async
DATABASE_URL = settings.DATABASE_URL

# Supabase uses postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Handle SQLite vs PostgreSQL
if DATABASE_URL.startswith("sqlite:///"):
    # Extract the database file path and ensure directory exists
    # sqlite:///./file.db (relative) or sqlite:////absolute/path/file.db (absolute)
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if db_path.startswith("/"):
        # Absolute path (e.g., /opt/render/project/src/data/visa_monitor.db)
        db_dir = Path(db_path).parent
    else:
        # Relative path (e.g., ./visa_monitor.db)
        db_dir = Path(db_path).parent
    
    # Create directory if it doesn't exist
    if db_dir and str(db_dir) != ".":
        os.makedirs(db_dir, exist_ok=True)
        print(f"Ensured database directory exists: {db_dir}")
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
    # Add SSL requirement for Supabase
    connect_args = {}
    if "supabase" in DATABASE_URL or "pooler.supabase" in DATABASE_URL:
        # Supabase requires SSL
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args = {"ssl": ssl_context}
    
    sync_engine = create_engine(
        DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )
    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        connect_args=connect_args,
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
