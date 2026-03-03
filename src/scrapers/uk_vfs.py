"""
UK VFS Global scraper - visa.vfsglobal.com
Logs in with user credentials and checks available appointment dates.
"""
import re
import time
import json
from typing import List, Optional, Tuple
from datetime import datetime
import logging

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, AvailabilityResult, ScraperRegistry
from .stealth import StealthBrowser

logger = logging.getLogger(__name__)


@ScraperRegistry.register
class UKVFSAccraScraper(BaseScraper):
    """
    Scraper for UK Visa appointments via VFS Global in Accra.
    Requires the user''s VFS Global account email + password.
    """

    EMBASSY_NAME = "uk_vfs_accra"
    BASE_URL = "https://visa.vfsglobal.com"
    COUNTRY = "gh"           # Ghana
    NATIONALITY = "en"
    MISSION_CODE = "gbr"     # UK / Great Britain

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        super().__init__()
        self.username = username
        self.password = password

    @property
    def login_url(self) -> str:
        return f"{self.BASE_URL}/{self.COUNTRY}/{self.NATIONALITY}/{self.MISSION_CODE}/login"

    @property
    def dashboard_url(self) -> str:
        return f"{self.BASE_URL}/{self.COUNTRY}/{self.NATIONALITY}/{self.MISSION_CODE}/application-detail"

    @property
    def slots_url(self) -> str:
        """VFS API endpoint to check appointment slots."""
        return f"{self.BASE_URL}/api/appointment/slots"

    async def login(self) -> Tuple[bool, str]:
        """
        Log in to VFS Global with stored credentials.
        Returns (success, message).
        """
        if not self.username or not self.password:
            return False, "No credentials provided"

        browser = await self.get_browser()
        client = browser.client

        try:
            # Step 1: GET login page to extract CSRF token
            resp = await client.get(self.login_url, timeout=30)
            if resp.status_code not in (200, 302):
                return False, f"Login page returned HTTP {resp.status_code}"

            soup = BeautifulSoup(resp.text, "lxml")

            # VFS uses Angular/hidden input CSRF tokens
            csrf = ""
            csrf_input = soup.find("input", {"name": "_token"}) or \
                         soup.find("input", {"name": "csrf_token"}) or \
                         soup.find("input", {"name": "__RequestVerificationToken"})
            if csrf_input:
                csrf = csrf_input.get("value", "")

            # Step 2: POST login credentials
            login_resp = await client.post(
                self.login_url,
                data={
                    "LoginForm[username]": self.username,
                    "LoginForm[password]": self.password,
                    "_token": csrf,
                    "login-button": "",
                },
                headers={
                    "Referer": self.login_url,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=30,
                follow_redirects=True,
            )

            final_url = str(login_resp.url)
            body_lower = login_resp.text.lower()

            if (
                "invalid" in body_lower
                or "incorrect" in body_lower
                or "login" in final_url
            ):
                return False, "Invalid username or password"

            self.logger.info(f"VFS login successful for {self.username}")
            return True, "Login successful"

        except httpx.TimeoutException:
            return False, "Login timed out"
        except Exception as e:
            self.logger.error(f"VFS login error: {e}")
            return False, str(e)[:100]

    async def _fetch_available_slots(self, client: httpx.AsyncClient) -> List[str]:
        """
        After login, check the VFS appointment slots API or calendar page.
        """
        dates = []
        try:
            # Try the VFS dashboard / application detail page
            resp = await client.get(self.dashboard_url, timeout=30)
            if resp.status_code != 200:
                return []

            # Look for date patterns in the response
            text = resp.text
            # ISO dates from JSON or HTML
            raw_dates = re.findall(r'"(\d{4}-\d{2}-\d{2})"', text)
            raw_dates += re.findall(r'(\d{2}/\d{2}/\d{4})', text)  # DD/MM/YYYY

            today = datetime.now().date()
            for d in raw_dates:
                try:
                    if "-" in d:
                        date_obj = datetime.strptime(d, "%Y-%m-%d").date()
                    else:
                        date_obj = datetime.strptime(d, "%d/%m/%Y").date()
                    if date_obj >= today:
                        dates.append(date_obj.strftime("%Y-%m-%d"))
                except ValueError:
                    pass

            dates = sorted(set(dates))
        except Exception as e:
            self.logger.warning(f"VFS slots fetch error: {e}")

        return dates

    async def check_availability(self) -> AvailabilityResult:
        """Login then check available appointment dates."""
        start_time = time.time()

        if not self.username or not self.password:
            return self._create_error_result("no_credentials")

        logged_in, login_msg = await self.login()
        if not logged_in:
            return self._create_error_result(f"login_failed: {login_msg}"[:50])

        try:
            browser = await self.get_browser()
            available_dates = await self._fetch_available_slots(browser.client)
            duration_ms = int((time.time() - start_time) * 1000)

            self.logger.info(
                f"VFS check done. slots={bool(available_dates)}, "
                f"dates={len(available_dates)}"
            )
            return self._create_success_result(
                slots_available=bool(available_dates),
                available_dates=available_dates,
                duration_ms=duration_ms,
            )

        except httpx.TimeoutException:
            return self._create_error_result("timeout")
        except Exception as e:
            self.logger.error(f"VFS check error: {e}")
            return self._create_error_result(str(e)[:50])

    async def parse_available_dates(self, page_content: str) -> List[str]:
        """Not used in authenticated flow - required by ABC."""
        return []


@ScraperRegistry.register
class UKVFSLagosScraper(UKVFSAccraScraper):
    """Scraper for UK VFS Lagos - same system, Nigeria."""

    EMBASSY_NAME = "uk_vfs_lagos"
    COUNTRY = "ng"
