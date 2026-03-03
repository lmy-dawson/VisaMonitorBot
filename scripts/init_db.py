"""
Database initialization script
Run this to create all tables in the database
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Base, sync_engine
from src.models import User, Monitor, Alert, AvailabilityLog, ScraperHealth


def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    
    # Create all tables
    Base.metadata.create_all(bind=sync_engine)
    
    print("Database tables created successfully!")
    print("\nTables created:")
    for table in Base.metadata.tables:
        print(f"  - {table}")


if __name__ == "__main__":
    init_database()
