"""
US Embassy Accra scraper - uses the AIS (ais.usvisa-info.com) CGI Federal system
Monitors appointment availability for US visa appointments in Ghana
"""
import re
import time
from typing import List, Optional
from datetime import datetime
import logging

import httpx

from .base import BaseScraper, AvailabilityResult, ScraperRegistry
from .stealth import StealthBrowser

logger = logging.getLogger(__name__)


@ScraperRegistry.register
class USEmbassyAccraScraper(BaseScraper):
    """
    Scraper for US Embassy Accra appointment availability.
    Uses the CGI Federal AIS system at ais.usvisa-info.com
    """
    
    EMBASSY_NAME = "us_accra"
    # Updated URL - ustraveldocs.com redirected to CGI Federal AIS system
    BASE_URL = "https://ais.usvisa-info.com/en-gh/niv"
    APPOINTMENT_URL = "https://ais.usvisa-info.com/en-gh/niv"
    
    async def check_availability(self) -> AvailabilityResult:
        """
        Check US Embassy Accra (AIS system) for available appointment slots.
        """
        start_time = time.time()
        
        try:
            browser = await self.get_browser()
            await StealthBrowser.random_delay(1, 3)
            
            self.logger.info(f"Navigating to {self.APPOINTMENT_URL}")
            
            try:
                content = await browser.goto(self.APPOINTMENT_URL, timeout=30000)
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if status_code == 403:
                    self.logger.warning("AIS site returned 403 - bot protection active")
                    return self._create_error_result("site_blocked_403")
                elif status_code == 404:
                    self.logger.warning("AIS site returned 404 - URL may have changed")
                    return self._create_error_result("site_not_found_404")
                else:
                    return self._create_error_result(f"HTTP {status_code}")
            
            if not content:
                return self._create_error_result("empty response")
            
            await StealthBrowser.random_delay(1, 2)
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
            
        except httpx.TimeoutException:
            self.logger.error("Request timed out")
            return self._create_error_result("timeout")
        except Exception as e:
            self.logger.error(f"Error checking availability: {str(e)}")
            return self._create_error_result(str(e)[:80])
    
    async def parse_available_dates(self, page_content: str) -> List[str]:
        """
        Parse available appointment dates from the AIS page content.
        The AIS system shows dates in ISO and US formats.
        """
        available_dates = []
        
        # AIS system date patterns
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',           # ISO: YYYY-MM-DD
            r'(\d{1,2}/\d{1,2}/\d{4})',       # US: MM/DD/YYYY
            r'available["\s:]+(\d{4}-\d{2}-\d{2})',  # Explicit available
        ]
        
        # Check for no-appointment indicators first
        no_appt_indicators = [
            "no appointments available",
            "no available appointments",
            "currently no appointments",
            "no slots available",
            "fully booked",
            "there are no",
        ]
        content_lower = page_content.lower()
        for indicator in no_appt_indicators:
            if indicator in content_lower:
                self.logger.info(f"Found no-appointment indicator: {indicator}")
                return []
        
        for pattern in date_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches:
                try:
                    if '-' in match:
                        date_obj = datetime.strptime(match, "%Y-%m-%d")
                    elif match.count('/') == 2:
                        try:
                            date_obj = datetime.strptime(match, "%m/%d/%Y")
                        except ValueError:
                            date_obj = datetime.strptime(match, "%Y/%m/%d")
                    else:
                        continue
                    
                    if date_obj > datetime.now():
                        date_str = date_obj.strftime("%Y-%m-%d")
                        if date_str not in available_dates:
                            available_dates.append(date_str)
                except ValueError:
                    continue
        
        return sorted(available_dates)


@ScraperRegistry.register
class USEmbassyLagosScraper(USEmbassyAccraScraper):
    """Scraper for US Embassy Lagos - uses AIS system for Nigeria"""
    
    EMBASSY_NAME = "us_lagos"
    BASE_URL = "https://ais.usvisa-info.com/en-ng/niv"
    APPOINTMENT_URL = "https://ais.usvisa-info.com/en-ng/niv"
