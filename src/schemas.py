"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# Enums matching database models
class NotificationPreference(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    BOTH = "both"


class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    AGENT = "agent"


class EmbassyType(str, Enum):
    US_ACCRA = "us_accra"
    UK_VFS_ACCRA = "uk_vfs_accra"
    SCHENGEN_ACCRA = "schengen_accra"
    US_LAGOS = "us_lagos"
    UK_VFS_LAGOS = "uk_vfs_lagos"
    CUSTOM = "custom"


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    notification_preference: NotificationPreference = NotificationPreference.TELEGRAM


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    telegram_chat_id: Optional[str] = None
    whatsapp_number: Optional[str] = None


class UserUpdate(BaseModel):
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    notification_preference: Optional[NotificationPreference] = None


class UserResponse(UserBase):
    id: int
    telegram_chat_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    plan: PlanType
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Monitor schemas
class MonitorBase(BaseModel):
    embassy: EmbassyType
    custom_url: Optional[str] = None  # For custom embassy type
    visa_type: Optional[str] = None
    preferred_date_from: Optional[datetime] = None
    preferred_date_to: Optional[datetime] = None


class MonitorCreate(MonitorBase):
    embassy_username: Optional[str] = None   # login email/username for the embassy site
    embassy_password: Optional[str] = None   # plaintext password (encrypted before storing)


class MonitorUpdate(BaseModel):
    embassy: Optional[EmbassyType] = None
    custom_url: Optional[str] = None
    visa_type: Optional[str] = None
    preferred_date_from: Optional[datetime] = None
    preferred_date_to: Optional[datetime] = None
    is_active: Optional[bool] = None


class MonitorResponse(MonitorBase):
    id: int
    user_id: int
    is_active: bool
    embassy_username: Optional[str] = None
    login_status: Optional[str] = None       # login_ok / login_failed / not_set
    login_verified_at: Optional[datetime] = None
    last_checked_at: Optional[datetime] = None
    last_check_status: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Alert schemas
class AlertBase(BaseModel):
    embassy: EmbassyType
    slot_date: Optional[datetime] = None
    available_dates: Optional[List[str]] = None
    message: str


class AlertResponse(AlertBase):
    id: int
    user_id: int
    monitor_id: int
    sent_via: NotificationPreference
    sent_at: datetime
    delivered: bool
    booked: bool
    booked_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MarkBookedRequest(BaseModel):
    booked: bool = True


# Availability schemas
class AvailabilityCheck(BaseModel):
    embassy: EmbassyType
    slots_available: bool
    available_dates: Optional[List[str]] = None
    checked_at: datetime
    
    class Config:
        from_attributes = True


# Telegram setup schemas
class TelegramSetup(BaseModel):
    telegram_chat_id: str


class TelegramVerifyResponse(BaseModel):
    verified: bool
    message: str


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
