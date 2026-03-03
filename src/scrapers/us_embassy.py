"""
US Embassy Accra (ustraveldocs.com) scraper
Monitors appointment availability for US visa appointments in Ghana
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
class USEmbassyAccraScraper(BaseScraper):
    """
    Scraper for US Embassy Accra appointment availability.
    
    Note: ustraveldocs.com structure may vary. This is a template
    that needs to be adjusted based on actual page structure.
    """
    
    EMBASSY_NAME = "us_accra"
    BASE_URL = "https://www.ustraveldocs.com/gh/en/"
    APPOINTMENT_URL = "https://www.ustraveldocs.com/gh/en/"
    
    # CSS selectors - these need to be updated based on actual site structure
    SELECTORS = {
        "availability_section": ".appointment-availability",
        "available_dates": ".available-date",
        "no_appointments": ".no-appointments-message",
        "calendar": ".calendar-container",
        "date_cell": ".calendar-day.available"
    }
    
    async def check_availability(self) -> AvailabilityResult:
        """
        Check US Embassy Accra for available appointment slots.
        
        Returns:
            AvailabilityResult with slot information
        """
        start_time = time.time()
        
        try:
            browser = await self.get_browser()
            
            # Add random delay before navigation
            await StealthBrowser.random_delay(1, 3)
            
            self.logger.info(f"Navigating to {self.APPOINTMENT_URL}")
            
            # Navigate to the appointment page and get content
            content = await browser.goto(self.APPOINTMENT_URL, timeout=30000)
            
            if not content:
                return self._create_error_result("Failed to load page: empty response")
            
            # Add delay to appear human-like
            await StealthBrowser.random_delay(2, 4)
            
            # Parse available dates from content
            available_dates = await self.parse_available_dates(content)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            slots_available = len(available_dates) > 0
            
            self.logger.info(
                f"Check complete. Slots available: {slots_available}, "
                f"Dates found: {len(available_dates)}"
            )
            
            return self._create_success_result(
                slots_available=slots_available,
                available_dates=available_dates,
                raw_response=content[:5000] if content else None,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            self.logger.error(f"Error checking availability: {str(e)}")
            return self._create_error_result(str(e))
    
    async def parse_available_dates(self, page_content: str) -> List[str]:
        """
        Parse available appointment dates from the page content.
        
        This method needs to be customized based on the actual
        structure of the ustraveldocs.com website.
        
        Args:
            page_content: HTML content from the page
            
        Returns:
            List of available date strings (format: YYYY-MM-DD)
        """
        available_dates = []
        
        # Try to find dates in various formats
        # Pattern 1: Explicit available dates
        date_patterns = [
            r'available["\s:]+(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
            r'(\d{4}/\d{2}/\d{2})',  # YYYY/MM/DD
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches:
                try:
                    # Try to parse and standardize the date
                    if '-' in match:
                        date_obj = datetime.strptime(match, "%Y-%m-%d")
                    elif match.count('/') == 2:
                        # Try both formats
                        try:
                            date_obj = datetime.strptime(match, "%m/%d/%Y")
                        except ValueError:
                            date_obj = datetime.strptime(match, "%Y/%m/%d")
                    else:
                        continue
                    
                    # Only include future dates
                    if date_obj > datetime.now():
                        date_str = date_obj.strftime("%Y-%m-%d")
                        if date_str not in available_dates:
                            available_dates.append(date_str)
                except ValueError:
                    continue
        
        # Check for "no appointments available" message
        no_appt_indicators = [
            "no appointments available",
            "no available appointments",
            "currently no appointments",
            "no slots available",
            "fully booked"
        ]
        
        content_lower = page_content.lower()
        for indicator in no_appt_indicators:
            if indicator in content_lower:
                self.logger.info(f"Found no-appointment indicator: {indicator}")
                return []  # Return empty list
        
        return sorted(available_dates)


@ScraperRegistry.register
class USEmbassyLagosScraper(USEmbassyAccraScraper):
    """Scraper for US Embassy Lagos - same structure as Accra"""
    
    EMBASSY_NAME = "us_lagos"
    BASE_URL = "https://www.ustraveldocs.com/ng/en/"
    APPOINTMENT_URL = "https://www.ustraveldocs.com/ng/en/"
