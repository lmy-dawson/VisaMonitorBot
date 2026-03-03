"""
Configuration settings for Visa Monitor Bot
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database (SQLite by default)
    DATABASE_URL: str = "sqlite:///./visa_monitor.db"
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    
    # Twilio (WhatsApp)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    
    # Proxy settings (for rotating proxies)
    PROXY_URL: Optional[str] = None
    USE_PROXY: bool = False
    
    # Scraping settings
    CHECK_INTERVAL_MINUTES: int = 5
    MIN_DELAY_SECONDS: int = 2
    MAX_DELAY_SECONDS: int = 8
    BACKOFF_MINUTES: int = 30
    MAX_FAILURES_BEFORE_PAUSE: int = 3
    
    # Environment
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # User agent rotation list
    USER_AGENTS: list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
