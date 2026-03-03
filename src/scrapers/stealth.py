"""
HTTP client for scraping embassy websites
Uses httpx with stealth headers for reliability on Windows
"""
import random
import asyncio
import httpx
from typing import Optional, Dict
from ..config import settings


class StealthBrowser:
    """
    HTTP client wrapper with stealth headers.
    Uses httpx for async HTTP requests - more reliable than Playwright on Windows.
    """
    
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self._user_agent: str = self._get_random_user_agent()
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    def _get_random_user_agent(self) -> str:
        """Get a random user agent from the configured list"""
        return random.choice(settings.USER_AGENTS)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get stealth headers"""
        return {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
    
    async def start(self):
        """Start the HTTP client"""
        # Configure proxy if enabled
        proxy = None
        if settings.USE_PROXY and settings.PROXY_URL:
            proxy = settings.PROXY_URL
        
        self.client = httpx.AsyncClient(
            headers=self._get_headers(),
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            proxy=proxy,
        )
        return self
    
    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    @staticmethod
    async def random_delay(min_seconds: float = None, max_seconds: float = None):
        """Add a random delay to appear more human-like"""
        min_s = min_seconds or settings.MIN_DELAY_SECONDS
        max_s = max_seconds or settings.MAX_DELAY_SECONDS
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)
    
    async def goto(self, url: str, timeout: int = 30000) -> str:
        """Navigate to URL and return page content"""
        if not self.client:
            await self.start()
        
        timeout_seconds = timeout / 1000
        response = await self.client.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        return response.text
    
    async def get_content(self) -> str:
        """Get last response content - for compatibility"""
        return ""
    
    async def new_page(self):
        """For compatibility with old interface"""
        return self


async def create_stealth_browser() -> StealthBrowser:
    """Factory function to create and start a stealth browser"""
    browser = StealthBrowser()
    await browser.start()
    return browser
