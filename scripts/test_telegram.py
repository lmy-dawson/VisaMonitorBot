"""
Test Telegram bot functionality
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notifications.telegram_bot import telegram_notifier, send_telegram_alert


async def test_telegram_alert():
    """Test sending a Telegram alert"""
    print("\n" + "="*50)
    print("Testing Telegram Alert")
    print("="*50)
    
    # Replace with your actual chat ID for testing
    test_chat_id = input("Enter your Telegram chat ID: ").strip()
    
    if not test_chat_id:
        print("No chat ID provided, skipping test")
        return
    
    # Initialize the notifier
    await telegram_notifier.initialize()
    
    # Send test alert
    success = await send_telegram_alert(
        chat_id=test_chat_id,
        embassy="us_accra",
        available_dates=["2026-03-15", "2026-03-18", "2026-03-22"],
    )
    
    if success:
        print("✅ Telegram alert sent successfully!")
    else:
        print("❌ Failed to send Telegram alert")


async def main():
    print("\nVisa Monitor Bot - Telegram Test")
    print("="*50)
    print("\nMake sure you have set TELEGRAM_BOT_TOKEN in your .env file")
    print("Also make sure you've started a chat with your bot first\n")
    
    await test_telegram_alert()


if __name__ == "__main__":
    asyncio.run(main())
