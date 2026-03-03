"""
Base scraper class for embassy availability checking
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
import logging

from .stealth import StealthBrowser

logger = logging.getLogger(__name__)


@dataclass
class AvailabilityResult:
    """Result of an availability check"""
    embassy: str
    slots_available: bool
    available_dates: List[str]
    raw_response: Optional[str] = None
    check_duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    success: bool = True
    checked_at: datetime = None
    
    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.utcnow()


class BaseScraper(ABC):
    """
    Abstract base class for embassy scrapers.
    Each embassy/booking system should implement its own scraper.
    """
    
    EMBASSY_NAME: str = "base"
    BASE_URL: str = ""
    
    def __init__(self):
        self.browser: Optional[StealthBrowser] = None
        self.logger = logging.getLogger(f"{__name__}.{self.EMBASSY_NAME}")
    
    @abstractmethod
    async def check_availability(self) -> AvailabilityResult:
        """
        Check for available appointment slots.
        Must be implemented by each scraper.
        
        Returns:
            AvailabilityResult with slot information
        """
        pass
    
    @abstractmethod
    async def parse_available_dates(self, page_content: str) -> List[str]:
        """
        Parse available dates from page content.
        Must be implemented by each scraper.
        
        Args:
            page_content: HTML or JSON content from the page
            
        Returns:
            List of available date strings
        """
        pass
    
    async def get_browser(self) -> StealthBrowser:
        """Get or create stealth browser instance"""
        if not self.browser:
            self.browser = StealthBrowser()
            await self.browser.start()
        return self.browser
    
    async def close(self):
        """Close browser if open"""
        if self.browser:
            await self.browser.close()
            self.browser = None
    
    async def __aenter__(self):
        await self.get_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _create_error_result(self, error_message: str) -> AvailabilityResult:
        """Create an error result"""
        return AvailabilityResult(
            embassy=self.EMBASSY_NAME,
            slots_available=False,
            available_dates=[],
            error_message=error_message,
            success=False
        )
    
    def _create_success_result(
        self,
        slots_available: bool,
        available_dates: List[str],
        raw_response: str = None,
        duration_ms: int = None
    ) -> AvailabilityResult:
        """Create a success result"""
        return AvailabilityResult(
            embassy=self.EMBASSY_NAME,
            slots_available=slots_available,
            available_dates=available_dates,
            raw_response=raw_response,
            check_duration_ms=duration_ms,
            success=True
        )


class ScraperRegistry:
    """Registry for managing multiple scrapers"""
    
    _scrapers: Dict[str, type] = {}
    
    @classmethod
    def register(cls, scraper_class: type):
        """Register a scraper class"""
        cls._scrapers[scraper_class.EMBASSY_NAME] = scraper_class
        return scraper_class
    
    @classmethod
    def get(cls, embassy_name: str) -> Optional[type]:
        """Get a scraper class by embassy name"""
        return cls._scrapers.get(embassy_name)
    
    @classmethod
    def get_all(cls) -> Dict[str, type]:
        """Get all registered scrapers"""
        return cls._scrapers.copy()
    
    @classmethod
    def list_embassies(cls) -> List[str]:
        """List all registered embassy names"""
        return list(cls._scrapers.keys())
