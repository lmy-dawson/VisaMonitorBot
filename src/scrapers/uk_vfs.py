"""
UK VFS Global scraper
Monitors appointment availability for UK visa appointments in Ghana
"""
import re
import time
import json
from typing import List, Optional
from datetime import datetime
import logging

import httpx

from .base import BaseScraper, AvailabilityResult, ScraperRegistry
from .stealth import StealthBrowser

logger = logging.getLogger(__name__)


@ScraperRegistry.register
class UKVFSAccraScraper(BaseScraper):
    """
    Scraper for UK Visa appointments via VFS Global in Accra.
    VFS Global redirects vfsglobal.co.uk -> visa.vfsglobal.com
    The site is heavily protected against bots (returns 403 to plain httpx).
    """
    
    EMBASSY_NAME = "uk_vfs_accra"
    # Corrected: old vfsglobal.co.uk/gh redirects to visa.vfsglobal.com/gh
    BASE_URL = "https://visa.vfsglobal.com/gh/en/gbr/information"
    
    async def check_availability(self) -> AvailabilityResult:
        """
        Check VFS Global for UK visa appointment availability in Accra.
        """
        start_time = time.time()
        
        try:
            browser = await self.get_browser()
            await StealthBrowser.random_delay(1, 3)
            
            self.logger.info(f"Navigating to {self.BASE_URL}")
            
            try:
                content = await browser.goto(self.BASE_URL, timeout=30000)
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if status_code == 403:
                    self.logger.warning("VFS site returned 403 - bot protection active")
                    return self._create_error_result("site_blocked_403")
                elif status_code == 404:
                    self.logger.warning("VFS URL returned 404")
                    return self._create_error_result("site_not_found_404")
                else:
                    return self._create_error_result(f"HTTP {status_code}")
            
            if not content:
                return self._create_error_result("empty response")
            
            await StealthBrowser.random_delay(1, 3)
            available_dates = await self.parse_available_dates(content)
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
            
        except httpx.TimeoutException:
            self.logger.error("VFS request timed out")
            return self._create_error_result("timeout")
        except Exception as e:
            self.logger.error(f"Error checking VFS availability: {str(e)}")
            return self._create_error_result(str(e)[:80])
    
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
    BASE_URL = "https://visa.vfsglobal.com/ng/en/gbr/information"
