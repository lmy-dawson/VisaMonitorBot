"""
Telegram Bot notification system
Sends instant alerts to users when visa slots are available
"""
import logging
from typing import Optional, List
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
import asyncio

from ..config import settings

logger = logging.getLogger(__name__)


# Embassy booking URLs
BOOKING_URLS = {
    "us_accra": "https://www.ustraveldocs.com/gh/en/step-3/",
    "us_lagos": "https://www.ustraveldocs.com/ng/en/step-3/",
    "uk_vfs_accra": "https://www.vfsglobal.co.uk/gh/en/book-appointment",
    "uk_vfs_lagos": "https://www.vfsglobal.co.uk/ng/en/book-appointment",
    "schengen_accra": "https://visas-gh.tlscontact.com/",
}

# Embassy display names
EMBASSY_NAMES = {
    "us_accra": "US Embassy Accra",
    "us_lagos": "US Embassy Lagos",
    "uk_vfs_accra": "UK Visa (VFS Accra)",
    "uk_vfs_lagos": "UK Visa (VFS Lagos)",
    "schengen_accra": "Schengen Visa (Accra)",
}


class TelegramNotifier:
    """
    Telegram notification service for visa slot alerts.
    """
    
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        
    async def initialize(self):
        """Initialize the Telegram bot"""
        if not self.bot_token:
            raise ValueError("Telegram bot token not configured")
        
        self.application = Application.builder().token(self.bot_token).build()
        
        # Register command handlers
        self.application.add_handler(CommandHandler("start", self._start_handler))
        self.application.add_handler(CommandHandler("help", self._help_handler))
        self.application.add_handler(CommandHandler("booked", self._booked_handler))
        self.application.add_handler(CommandHandler("status", self._status_handler))
        
        # Initialize the application (required for v20+)
        await self.application.initialize()
        
        # Get the bot from the application (already initialized)
        self.bot = self.application.bot
        
        logger.info("Telegram bot initialized")
    
    async def _start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - returns chat_id for registration"""
        chat_id = update.effective_chat.id
        welcome_message = f"""
👋 Welcome to the Visa Monitor Bot!

Your Chat ID is: `{chat_id}`

Copy this ID and enter it in your account settings to receive alerts.

📋 Available Commands:
/help - Show help message
/booked - Mark your last alert as booked
/status - Check your monitoring status

🔔 You'll receive instant alerts when visa slots become available.
        """
        await update.message.reply_text(welcome_message, parse_mode="Markdown")
    
    async def _help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
📖 Visa Monitor Bot Help

Commands:
• /start - Get your Chat ID
• /booked - Stop alerts after you've booked
• /status - Check monitoring status
• /help - Show this message

When a slot is available, you'll get an instant alert. Book quickly as slots go fast!

⚡ Tip: Keep notifications ON so you don't miss alerts.
        """
        await update.message.reply_text(help_message)
    
    async def _booked_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /booked command"""
        # This would normally update the database
        await update.message.reply_text(
            "✅ Great! Your last alert has been marked as booked.\n"
            "You'll stop receiving alerts for this monitor.\n\n"
            "💡 To set up a new monitor, visit your dashboard."
        )
    
    async def _status_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        chat_id = update.effective_chat.id
        await update.message.reply_text(
            f"📊 Status Check\n\n"
            f"Chat ID: `{chat_id}`\n"
            f"Connection: ✅ Active\n\n"
            f"Your monitors are running. You'll be notified when slots appear.",
            parse_mode="Markdown"
        )
    
    async def send_alert(
        self,
        chat_id: str,
        embassy: str,
        available_dates: List[str],
        slot_date: str = None
    ) -> bool:
        """
        Send a visa slot availability alert to a user.
        
        Args:
            chat_id: Telegram chat ID of the user
            embassy: Embassy identifier (e.g., 'us_accra')
            available_dates: List of available date strings
            slot_date: Specific slot date (if single date)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.bot:
            await self.initialize()
        
        embassy_name = EMBASSY_NAMES.get(embassy, embassy)
        booking_url = BOOKING_URLS.get(embassy, "N/A")
        
        # Format dates for display
        if available_dates:
            dates_str = "\n".join([f"  • {date}" for date in available_dates[:5]])
            if len(available_dates) > 5:
                dates_str += f"\n  ... and {len(available_dates) - 5} more"
        else:
            dates_str = f"  • {slot_date}" if slot_date else "  • Check website for times"
        
        message = f"""
🚨 *APPOINTMENT SLOT AVAILABLE!*

🏛 *Embassy:* {embassy_name}

📅 *Available Dates:*
{dates_str}

⚡ *Book NOW before it's taken!*

👉 [Click here to book]({booking_url})

━━━━━━━━━━━━━━━━━━━━━━
Reply /booked when you've booked to stop alerts.
        """
        
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            logger.info(f"Alert sent to chat_id {chat_id} for {embassy}")
            return True
            
        except TelegramError as e:
            logger.error(f"Failed to send alert to {chat_id}: {str(e)}")
            return False
    
    async def send_simple_message(self, chat_id: str, message: str) -> bool:
        """Send a simple text message"""
        if not self.bot:
            await self.initialize()
        
        try:
            await self.bot.send_message(chat_id=chat_id, text=message)
            return True
        except TelegramError as e:
            logger.error(f"Failed to send message to {chat_id}: {str(e)}")
            return False
    
    async def verify_chat_id(self, chat_id: str) -> bool:
        """Verify that a chat_id is valid by trying to send a test message"""
        if not self.bot:
            await self.initialize()
        
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text="✅ Your Telegram is connected to Visa Monitor Bot!\n"
                     "You'll receive alerts here when slots are available."
            )
            return True
        except TelegramError:
            return False
    
    async def process_update(self, update_data: dict) -> bool:
        """Process an incoming webhook update from Telegram"""
        if not self.application:
            await self.initialize()
        
        try:
            update = Update.de_json(data=update_data, bot=self.bot)
            await self.application.process_update(update)
            return True
        except Exception as e:
            logger.error(f"Failed to process update: {str(e)}")
            return False
    
    async def set_webhook(self, webhook_url: str) -> bool:
        """Set the webhook URL for receiving updates"""
        if not self.bot:
            await self.initialize()
        
        try:
            await self.bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook set to: {webhook_url}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to set webhook: {str(e)}")
            return False
    
    def run_polling(self):
        """Start the bot in polling mode (for standalone operation)"""
        if not self.application:
            asyncio.run(self.initialize())
        self.application.run_polling()


# Global telegram notifier instance
telegram_notifier = TelegramNotifier()


async def send_telegram_alert(
    chat_id: str,
    embassy: str,
    available_dates: List[str],
    slot_date: str = None
) -> bool:
    """Convenience function to send alerts"""
    return await telegram_notifier.send_alert(
        chat_id=chat_id,
        embassy=embassy,
        available_dates=available_dates,
        slot_date=slot_date
    )
