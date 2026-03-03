"""
Schengen visa scraper - VFS Global (visa.vfsglobal.com)
Handles appointment monitoring for Schengen countries processed via VFS Ghana.
Default target: Germany (MISSION_CODE = deu) — largest Schengen VFS user base in Ghana.
Subclass and change MISSION_CODE for other Schengen countries (ita, esp, fra, etc.)
"""
from typing import Optional

from .base import ScraperRegistry
from .uk_vfs import UKVFSAccraScraper

# ---------------------------------------------------------------------------
# Schengen – Accra  (Germany via VFS Global Ghana by default)
# ---------------------------------------------------------------------------

@ScraperRegistry.register
class SchengenAccraScraper(UKVFSAccraScraper):
    """
    Schengen visa appointments in Accra via VFS Global.
    Default mission: Germany (deu). Change MISSION_CODE for other countries.
    Requires the user-s VFS Global account credentials.
    """

    EMBASSY_NAME = "schengen_accra"
    COUNTRY = "gh"
    NATIONALITY = "en"
    MISSION_CODE = "fra"   # France — has active VFS web booking in Ghana

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        super().__init__(username=username, password=password)
