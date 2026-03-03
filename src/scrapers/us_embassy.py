"""
US Embassy Accra scraper - CGI Federal AIS system (ais.usvisa-info.com)
Logs in with user credentials and checks available appointment dates.
"""
import re
import time
from typing import List, Optional, Tuple
from datetime import datetime
import logging

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, AvailabilityResult, ScraperRegistry

logger = logging.getLogger(__name__)

# Known AIS facility IDs
AIS_FACILITY_ID = {
    "us_accra": 95,
    "us_lagos": 94,
}


@ScraperRegistry.register
class USEmbassyAccraScraper(BaseScraper):
    """
    Scraper for US Embassy Accra via the AIS system (ais.usvisa-info.com).
    Requires the user''s AIS account email + password to access the appointment calendar.
    """

    EMBASSY_NAME = "us_accra"
    BASE_URL = "https://ais.usvisa-info.com"
    COUNTRY_CODE = "en-gh"
    FACILITY_ID = AIS_FACILITY_ID["us_accra"]

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        super().__init__()
        self.username = username
        self.password = password

    @property
    def sign_in_url(self) -> str:
        return f"{self.BASE_URL}/{self.COUNTRY_CODE}/niv/users/sign_in"

    @property
    def dashboard_url(self) -> str:
        return f"{self.BASE_URL}/{self.COUNTRY_CODE}/niv/"

    def _days_url(self, application_id: int) -> str:
        return (
            f"{self.BASE_URL}/{self.COUNTRY_CODE}/niv/schedule/"
            f"{application_id}/appointment/days/{self.FACILITY_ID}.json"
            f"?appointments[expedite]=false"
        )

    async def login(self) -> Tuple[bool, str]:
        """
        Log in to the AIS system with stored credentials.
        Returns (success, message).
        """
        if not self.username or not self.password:
            return False, "No credentials provided"

        browser = await self.get_browser()
        client = browser.client

        try:
            # Step 1: GET sign-in page to extract CSRF token
            resp = await client.get(self.sign_in_url, timeout=30)
            if resp.status_code != 200:
                return False, f"Sign-in page returned HTTP {resp.status_code}"

            soup = BeautifulSoup(resp.text, "lxml")
            csrf_meta = soup.find("meta", {"name": "csrf-token"})
            if csrf_meta:
                csrf_token = csrf_meta.get("content", "")
            else:
                csrf_input = soup.find("input", {"name": "authenticity_token"})
                csrf_token = csrf_input["value"] if csrf_input else ""

            # Step 2: POST credentials
            login_resp = await client.post(
                self.sign_in_url,
                data={
                    "user[email]": self.username,
                    "user[password]": self.password,
                    "policy_confirmed": "1",
                    "commit": "Sign In",
                    "authenticity_token": csrf_token,
                },
                headers={
                    "Referer": self.sign_in_url,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=30,
                follow_redirects=True,
            )

            body_lower = login_resp.text.lower()
            final_url = str(login_resp.url)

            if "invalid email or password" in body_lower or "sign_in" in final_url:
                return False, "Invalid email or password"

            self.logger.info(f"AIS login successful for {self.username}")
            return True, "Login successful"

        except httpx.TimeoutException:
            return False, "Login timed out"
        except Exception as e:
            self.logger.error(f"AIS login error: {e}")
            return False, str(e)[:100]

    async def _get_application_ids(self, client: httpx.AsyncClient) -> List[int]:
        """Parse dashboard HTML to find active application/schedule IDs."""
        try:
            resp = await client.get(self.dashboard_url, timeout=30)
            matches = re.findall(r"/niv/schedule/(\d+)/", resp.text)
            return list(set(int(m) for m in matches))
        except Exception as e:
            self.logger.warning(f"Could not extract application IDs: {e}")
            return []

    async def _fetch_available_dates(self, client: httpx.AsyncClient, app_id: int) -> List[str]:
        """Hit the AIS JSON endpoint for available dates."""
        try:
            resp = await client.get(
                self._days_url(app_id),
                headers={
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": (
                        f"{self.BASE_URL}/{self.COUNTRY_CODE}/niv"
                        f"/schedule/{app_id}/appointment"
                    ),
                },
                timeout=20,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            today = datetime.now().date()
            dates = []
            for entry in data:
                if isinstance(entry, dict):
                    d = entry.get("date", "")
                    if d:
                        try:
                            if datetime.strptime(d, "%Y-%m-%d").date() >= today:
                                dates.append(d)
                        except ValueError:
                            pass
            return dates
        except Exception as e:
            self.logger.warning(f"AIS dates API error: {e}")
            return []

    async def check_availability(self) -> AvailabilityResult:
        """Login then fetch available appointment dates."""
        start_time = time.time()

        if not self.username or not self.password:
            return self._create_error_result("no_credentials")

        logged_in, login_msg = await self.login()
        if not logged_in:
            return self._create_error_result(f"login_failed: {login_msg}"[:50])

        try:
            browser = await self.get_browser()
            client = browser.client

            app_ids = await self._get_application_ids(client)
            if not app_ids:
                return self._create_success_result(
                    slots_available=False,
                    available_dates=[],
                    raw_response="Login OK - no active applications found",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            all_dates: List[str] = []
            for app_id in app_ids[:3]:
                all_dates.extend(await self._fetch_available_dates(client, app_id))

            available_dates = sorted(set(all_dates))
            duration_ms = int((time.time() - start_time) * 1000)

            self.logger.info(
                f"AIS check done. slots={len(available_dates) > 0}, "
                f"dates={len(available_dates)}"
            )
            return self._create_success_result(
                slots_available=bool(available_dates),
                available_dates=list(available_dates),
                duration_ms=duration_ms,
            )

        except httpx.TimeoutException:
            return self._create_error_result("timeout")
        except Exception as e:
            self.logger.error(f"AIS check error: {e}")
            return self._create_error_result(str(e)[:50])

    async def parse_available_dates(self, page_content: str) -> List[str]:
        """Not used in authenticated flow - required by ABC."""
        return []


@ScraperRegistry.register
class USEmbassyLagosScraper(USEmbassyAccraScraper):
    """Scraper for US Embassy Lagos - same AIS system, Nigeria country code."""

    EMBASSY_NAME = "us_lagos"
    COUNTRY_CODE = "en-ng"
    FACILITY_ID = AIS_FACILITY_ID["us_lagos"]
