"""
Test script to verify scrapers work correctly
Run manually to test scraper functionality
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scrapers.us_embassy import USEmbassyAccraScraper
from src.scrapers.uk_vfs import UKVFSAccraScraper
from src.scrapers.schengen import SchengenAccraScraper


async def test_us_embassy():
    """Test US Embassy Accra scraper"""
    print("\n" + "="*50)
    print("Testing US Embassy Accra Scraper")
    print("="*50)
    
    async with USEmbassyAccraScraper() as scraper:
        result = await scraper.check_availability()
        
        print(f"Success: {result.success}")
        print(f"Slots Available: {result.slots_available}")
        print(f"Available Dates: {result.available_dates}")
        print(f"Duration: {result.check_duration_ms}ms")
        
        if result.error_message:
            print(f"Error: {result.error_message}")
        
        return result


async def test_uk_vfs():
    """Test UK VFS Accra scraper"""
    print("\n" + "="*50)
    print("Testing UK VFS Accra Scraper")
    print("="*50)
    
    async with UKVFSAccraScraper() as scraper:
        result = await scraper.check_availability()
        
        print(f"Success: {result.success}")
        print(f"Slots Available: {result.slots_available}")
        print(f"Available Dates: {result.available_dates}")
        print(f"Duration: {result.check_duration_ms}ms")
        
        if result.error_message:
            print(f"Error: {result.error_message}")
        
        return result


async def test_schengen():
    """Test Schengen Accra scraper"""
    print("\n" + "="*50)
    print("Testing Schengen Accra Scraper")
    print("="*50)
    
    async with SchengenAccraScraper() as scraper:
        result = await scraper.check_availability()
        
        print(f"Success: {result.success}")
        print(f"Slots Available: {result.slots_available}")
        print(f"Available Dates: {result.available_dates}")
        print(f"Duration: {result.check_duration_ms}ms")
        
        if result.error_message:
            print(f"Error: {result.error_message}")
        
        return result


async def main():
    """Run all scraper tests"""
    print("\nVisa Monitor Bot - Scraper Test Suite")
    print("="*50)
    
    # Test each scraper
    # Note: These may fail if the actual websites have changed structure
    # The scrapers need to be customized for the actual website HTML
    
    try:
        await test_us_embassy()
    except Exception as e:
        print(f"US Embassy test failed: {e}")
    
    try:
        await test_uk_vfs()
    except Exception as e:
        print(f"UK VFS test failed: {e}")
    
    try:
        await test_schengen()
    except Exception as e:
        print(f"Schengen test failed: {e}")
    
    print("\n" + "="*50)
    print("Testing Complete")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
