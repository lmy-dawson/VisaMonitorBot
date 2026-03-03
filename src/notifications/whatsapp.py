"""
WhatsApp notification system via Twilio
Sends alerts to users via WhatsApp
"""
import logging
from typing import List, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from ..config import settings
from .telegram_bot import EMBASSY_NAMES, BOOKING_URLS

logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    """
    WhatsApp notification service via Twilio.
    
    Note: Twilio WhatsApp requires:
    1. A Twilio account with WhatsApp sandbox or approved number
    2. Users must first message your WhatsApp number to opt-in
    """
    
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_NUMBER
        self.client: Optional[Client] = None
        
    def _get_client(self) -> Client:
        """Get or create Twilio client"""
        if not self.client:
            if not all([self.account_sid, self.auth_token]):
                raise ValueError("Twilio credentials not configured")
            self.client = Client(self.account_sid, self.auth_token)
        return self.client
    
    def is_configured(self) -> bool:
        """Check if WhatsApp is configured"""
        return all([
            self.account_sid,
            self.auth_token,
            self.from_number
        ])
    
    async def send_alert(
        self,
        to_number: str,
        embassy: str,
        available_dates: List[str],
        slot_date: str = None
    ) -> bool:
        """
        Send a WhatsApp alert to a user.
        
        Args:
            to_number: User's WhatsApp number (with country code)
            embassy: Embassy identifier
            available_dates: List of available dates
            slot_date: Specific slot date
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("WhatsApp not configured, skipping alert")
            return False
        
        embassy_name = EMBASSY_NAMES.get(embassy, embassy)
        booking_url = BOOKING_URLS.get(embassy, "")
        
        # Format dates
        if available_dates:
            dates_str = ", ".join(available_dates[:3])
            if len(available_dates) > 3:
                dates_str += f" (+{len(available_dates) - 3} more)"
        else:
            dates_str = slot_date or "Check website"
        
        message = f"""🚨 VISA SLOT AVAILABLE!

🏛 {embassy_name}
📅 Dates: {dates_str}

⚡ Book NOW: {booking_url}

Reply BOOKED when done."""
        
        try:
            client = self._get_client()
            
            # Format numbers for WhatsApp
            from_whatsapp = f"whatsapp:{self.from_number}"
            to_whatsapp = f"whatsapp:{to_number}"
            
            message_response = client.messages.create(
                body=message,
                from_=from_whatsapp,
                to=to_whatsapp
            )
            
            logger.info(
                f"WhatsApp sent to {to_number}, SID: {message_response.sid}"
            )
            return True
            
        except TwilioRestException as e:
            logger.error(f"Failed to send WhatsApp to {to_number}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"WhatsApp error: {str(e)}")
            return False
    
    async def send_simple_message(self, to_number: str, message: str) -> bool:
        """Send a simple WhatsApp message"""
        if not self.is_configured():
            return False
        
        try:
            client = self._get_client()
            
            client.messages.create(
                body=message,
                from_=f"whatsapp:{self.from_number}",
                to=f"whatsapp:{to_number}"
            )
            return True
            
        except Exception as e:
            logger.error(f"WhatsApp error: {str(e)}")
            return False
    
    async def verify_number(self, to_number: str) -> bool:
        """
        Verify WhatsApp number by sending a test message.
        
        Note: User must have opted in to receive messages first.
        """
        return await self.send_simple_message(
            to_number,
            "✅ Your WhatsApp is connected to Visa Monitor Bot! "
            "You'll receive alerts here when slots are available."
        )


# Global WhatsApp notifier instance
whatsapp_notifier = WhatsAppNotifier()


async def send_whatsapp_alert(
    to_number: str,
    embassy: str,
    available_dates: List[str],
    slot_date: str = None
) -> bool:
    """Convenience function to send WhatsApp alerts"""
    return await whatsapp_notifier.send_alert(
        to_number=to_number,
        embassy=embassy,
        available_dates=available_dates,
        slot_date=slot_date
    )
