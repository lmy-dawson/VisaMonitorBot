"""
UK VFS Global scraper
Monitors appointment availability for UK visa appointments
"""
import re
import time
import json
from typing import List, Optional
from datetime import datetime
import logging

from .base import BaseScraper, AvailabilityResult, ScraperRegistry
from .stealth import StealthBrowser

logger = logging.getLogger(__name__)


@ScraperRegistry.register
class UKVFSAccraScraper(BaseScraper):
    """
    Scraper for UK Visa appointments via VFS Global in Accra.
    
    VFS Global websites often have JavaScript-heavy pages that
    load appointment data dynamically.
    """
    
    EMBASSY_NAME = "uk_vfs_accra"
    BASE_URL = "https://www.vfsglobal.co.uk/gh/en"
    
    # VFS often uses a specific endpoint for availability
    AVAILABILITY_ENDPOINT = "/appointment/check-appointment-availability"
    
    # CSS selectors - adjust based on actual VFS structure
    SELECTORS = {
        "appointment_section": "#appointmentSection",
        "available_slots": ".slot-available",
        "calendar": ".calendar-widget",
        "date_picker": ".date-picker",
        "available_day": ".day.available",
        "no_slots": ".no-slots-message"
    }
    
    async def check_availability(self) -> AvailabilityResult:
        """
        Check VFS Global for UK visa appointment availability.
        
        Returns:
            AvailabilityResult with slot information
        """
        start_time = time.time()
        
        try:
            browser = await self.get_browser()
            
            # Add random delay
            await StealthBrowser.random_delay(1, 3)
            
            self.logger.info(f"Navigating to {self.BASE_URL}")
            
            # Navigate to the VFS page and get content
            content = await browser.goto(self.BASE_URL, timeout=30000)
            
            if not content:
                return self._create_error_result("Failed to load page: empty response")
            
            # Add delay to appear human-like
            await StealthBrowser.random_delay(2, 5)
            
            # Parse available dates
            available_dates = await self.parse_available_dates(content)
            
            # Remove duplicates and sort
            available_dates = sorted(list(set(available_dates)))
            
            duration_ms = int((time.time() - start_time) * 1000)
            slots_available = len(available_dates) > 0
            
            self.logger.info(
                f"VFS check complete. Slots: {slots_available}, "
                f"Dates: {len(available_dates)}"
            )
            
            return self._create_success_result(
                slots_available=slots_available,
                available_dates=available_dates,
                raw_response=content[:5000],
                duration_ms=duration_ms
            )
            
        except Exception as e:
            self.logger.error(f"Error checking VFS availability: {str(e)}")
            return self._create_error_result(str(e))
    
    async def parse_available_dates(self, page_content: str) -> List[str]:
        """
        Parse available dates from VFS page content.
        
        Args:
            page_content: HTML content from the page
            
        Returns:
            List of available date strings
        """
        available_dates = []
        
        # Look for common VFS date patterns
        date_patterns = [
            # ISO format
            r'"date"\s*:\s*"(\d{4}-\d{2}-\d{2})"',
            # VFS specific formats
            r'availableDate["\s:]+(\d{4}-\d{2}-\d{2})',
            r'slot_date["\s:]+(\d{4}-\d{2}-\d{2})',
            # DD/MM/YYYY (common in UK)
            r'(\d{2}/\d{2}/\d{4})',
            # Data attributes
            r'data-date="(\d{4}-\d{2}-\d{2})"',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, page_content)
            for match in matches:
                try:
                    if '-' in match:
                        date_obj = datetime.strptime(match, "%Y-%m-%d")
                    else:
                        # Try DD/MM/YYYY for UK format
                        date_obj = datetime.strptime(match, "%d/%m/%Y")
                    
                    if date_obj > datetime.now():
                        date_str = date_obj.strftime("%Y-%m-%d")
                        if date_str not in available_dates:
                            available_dates.append(date_str)
                except ValueError:
                    continue
        
        return available_dates
    
    def _parse_json_dates(self, json_string: str) -> List[str]:
        """Try to extract dates from JSON data in scripts"""
        dates = []
        
        # Try to find JSON objects in the string
        json_pattern = r'\{[^{}]*"date"[^{}]*\}'
        matches = re.findall(json_pattern, json_string)
        
        for match in matches:
            try:
                data = json.loads(match)
                if 'date' in data and data.get('available', True):
                    dates.append(data['date'])
            except json.JSONDecodeError:
                continue
        
        return dates


@ScraperRegistry.register
class UKVFSLagosScraper(UKVFSAccraScraper):
    """Scraper for UK VFS Lagos"""
    
    EMBASSY_NAME = "uk_vfs_lagos"
    BASE_URL = "https://www.vfsglobal.co.uk/ng/en"
