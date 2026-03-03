"""
Schengen visa scraper (TLScontact / VFS)
Monitors appointment availability for Schengen visas
"""
import re
import time
from typing import List, Optional
from datetime import datetime
import logging

from .base import BaseScraper, AvailabilityResult, ScraperRegistry
from .stealth import StealthBrowser

logger = logging.getLogger(__name__)


@ScraperRegistry.register
class SchengenAccraScraper(BaseScraper):
    """
    Scraper for Schengen visa appointments in Accra.
    
    Note: Schengen visas are processed by different providers
    (TLScontact, VFS Global, BLS) depending on the country.
    This is a generic template that may need customization.
    """
    
    EMBASSY_NAME = "schengen_accra"
    BASE_URL = "https://visas-gh.tlscontact.com/"
    
    SELECTORS = {
        "calendar": ".appointment-calendar",
        "available_slot": ".slot-available",
        "date_cell": ".calendar-day",
    }
    
    async def check_availability(self) -> AvailabilityResult:
        """
        Check for Schengen visa appointment availability.
        
        Returns:
            AvailabilityResult with slot information
        """
        start_time = time.time()
        
        try:
            browser = await self.get_browser()
            
            await StealthBrowser.random_delay(1, 3)
            
            self.logger.info(f"Navigating to {self.BASE_URL}")
            
            # Navigate and get content
            content = await browser.goto(self.BASE_URL, timeout=30000)
            
            if not content:
                return self._create_error_result("Failed to load page: empty response")
            
            await StealthBrowser.random_delay(2, 4)
            
            available_dates = await self.parse_available_dates(content)
            
            duration_ms = int((time.time() - start_time) * 1000)
            slots_available = len(available_dates) > 0
            
            self.logger.info(
                f"Schengen check complete. Slots: {slots_available}, "
                f"Dates: {len(available_dates)}"
            )
            
            return self._create_success_result(
                slots_available=slots_available,
                available_dates=available_dates,
                raw_response=content[:5000],
                duration_ms=duration_ms
            )
            
        except Exception as e:
            self.logger.error(f"Error checking Schengen availability: {str(e)}")
            return self._create_error_result(str(e))
    
    async def parse_available_dates(self, page_content: str) -> List[str]:
        """Parse available dates from TLScontact page"""
        available_dates = []
        
        date_patterns = [
            r'"availableDate"\s*:\s*"(\d{4}-\d{2}-\d{2})"',
            r'data-date="(\d{4}-\d{2}-\d{2})"',
            r'appointment.*?(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',  # DD/MM/YYYY
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches:
                try:
                    if '-' in match:
                        date_obj = datetime.strptime(match, "%Y-%m-%d")
                    else:
                        date_obj = datetime.strptime(match, "%d/%m/%Y")
                    
                    if date_obj > datetime.now():
                        date_str = date_obj.strftime("%Y-%m-%d")
                        if date_str not in available_dates:
                            available_dates.append(date_str)
                except ValueError:
                    continue
        
        return sorted(available_dates)
