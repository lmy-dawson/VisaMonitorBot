"""
SQLAlchemy database models for Visa Monitor Bot
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from .database import Base


class NotificationPreference(str, enum.Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    BOTH = "both"


class PlanType(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    AGENT = "agent"


class EmbassyType(str, enum.Enum):
    US_ACCRA = "us_accra"
    UK_VFS_ACCRA = "uk_vfs_accra"
    SCHENGEN_ACCRA = "schengen_accra"
    US_LAGOS = "us_lagos"
    UK_VFS_LAGOS = "uk_vfs_lagos"
    CUSTOM = "custom"  # User-provided URL


class User(Base):
    """User model - stores user information and notification preferences"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    telegram_chat_id = Column(String(100), nullable=True, index=True)
    whatsapp_number = Column(String(50), nullable=True)
    notification_preference = Column(
        Enum(NotificationPreference),
        default=NotificationPreference.TELEGRAM
    )
    plan = Column(Enum(PlanType), default=PlanType.FREE)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    monitors = relationship("Monitor", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Monitor(Base):
    """Monitor model - stores user's monitoring preferences"""
    __tablename__ = "monitors"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    embassy = Column(Enum(EmbassyType), nullable=False)
    custom_url = Column(String(500), nullable=True)  # For custom embassy type
    visa_type = Column(String(100), nullable=True)  # e.g., "B1/B2", "tourist", "student"
    preferred_date_from = Column(DateTime, nullable=True)
    preferred_date_to = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    last_checked_at = Column(DateTime, nullable=True)  # Track last check time
    last_check_status = Column(String(50), nullable=True)  # success/error
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="monitors")
    alerts = relationship("Alert", back_populates="monitor", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Monitor(id={self.id}, embassy={self.embassy}, user_id={self.user_id})>"


class AvailabilityLog(Base):
    """Availability log - stores scraping results for each check"""
    __tablename__ = "availability_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    embassy = Column(Enum(EmbassyType), nullable=False, index=True)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    slots_available = Column(Boolean, default=False)
    available_dates = Column(JSON, nullable=True)  # List of available dates
    raw_response = Column(Text, nullable=True)  # Store raw HTML/JSON for debugging
    check_duration_ms = Column(Integer, nullable=True)  # How long the check took
    error_message = Column(Text, nullable=True)  # If check failed
    success = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<AvailabilityLog(id={self.id}, embassy={self.embassy}, slots={self.slots_available})>"


class Alert(Base):
    """Alert model - stores sent notifications"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    monitor_id = Column(Integer, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False)
    embassy = Column(Enum(EmbassyType), nullable=False)
    slot_date = Column(DateTime, nullable=True)
    available_dates = Column(JSON, nullable=True)  # Multiple dates if available
    message = Column(Text, nullable=False)
    sent_via = Column(Enum(NotificationPreference), nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered = Column(Boolean, default=False)
    booked = Column(Boolean, default=False)  # User marked as booked
    booked_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="alerts")
    monitor = relationship("Monitor", back_populates="alerts")
    
    def __repr__(self):
        return f"<Alert(id={self.id}, embassy={self.embassy}, booked={self.booked})>"


class ScraperHealth(Base):
    """Track scraper health and failures"""
    __tablename__ = "scraper_health"
    
    id = Column(Integer, primary_key=True, index=True)
    embassy = Column(Enum(EmbassyType), unique=True, nullable=False)
    consecutive_failures = Column(Integer, default=0)
    is_paused = Column(Boolean, default=False)
    paused_until = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    total_checks = Column(Integer, default=0)
    total_failures = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<ScraperHealth(embassy={self.embassy}, failures={self.consecutive_failures})>"
