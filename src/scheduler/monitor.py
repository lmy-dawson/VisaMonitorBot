"""
Visa appointment monitoring scheduler
Runs scrapers periodically and sends alerts when slots are found
"""
import logging
import httpx
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..config import settings
from ..database import SessionLocal
from ..models import (
    Monitor, User, Alert, AvailabilityLog, ScraperHealth,
    EmbassyType, NotificationPreference
)
from ..scrapers.base import ScraperRegistry, AvailabilityResult
from ..scrapers.us_embassy import USEmbassyAccraScraper, USEmbassyLagosScraper
from ..scrapers.uk_vfs import UKVFSAccraScraper, UKVFSLagosScraper
from ..scrapers.schengen import SchengenAccraScraper
from ..notifications.telegram_bot import send_telegram_alert
from ..notifications.whatsapp import send_whatsapp_alert

logger = logging.getLogger(__name__)


class VisaMonitorScheduler:
    """
    Scheduler that runs visa appointment checks at regular intervals.
    
    Architecture:
    1. Scheduler runs every X minutes (configurable)
    2. For each active embassy, check for available slots
    3. If slots found, find all users monitoring that embassy
    4. Send alerts to users via their preferred channel
    5. Log availability and track scraper health
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running = False
        
        # Map embassy types to scraper classes
        self.scraper_map: Dict[EmbassyType, type] = {
            EmbassyType.US_ACCRA: USEmbassyAccraScraper,
            EmbassyType.US_LAGOS: USEmbassyLagosScraper,
            EmbassyType.UK_VFS_ACCRA: UKVFSAccraScraper,
            EmbassyType.UK_VFS_LAGOS: UKVFSLagosScraper,
            EmbassyType.SCHENGEN_ACCRA: SchengenAccraScraper,
            # CUSTOM type will be handled separately with custom_url
        }
    
    def start(self):
        """Start the monitoring scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        # Add the main monitoring job
        self.scheduler.add_job(
            self.run_monitoring_cycle,
            trigger=IntervalTrigger(minutes=settings.CHECK_INTERVAL_MINUTES),
            id="visa_monitor_main",
            name="Visa Appointment Monitor",
            replace_existing=True,
        )
        
        # Add health check job
        self.scheduler.add_job(
            self.health_check,
            trigger=IntervalTrigger(hours=1),
            id="health_check",
            name="Scraper Health Check",
            replace_existing=True,
        )
        
        self.scheduler.start()
        self.running = True
        logger.info(
            f"Scheduler started. Checking every {settings.CHECK_INTERVAL_MINUTES} minutes"
        )
    
    def stop(self):
        """Stop the scheduler"""
        if self.running:
            self.scheduler.shutdown(wait=False)
            self.running = False
            logger.info("Scheduler stopped")
    
    async def run_monitoring_cycle(self):
        """
        Main monitoring cycle - runs all active scrapers and sends alerts.
        """
        logger.info("Starting monitoring cycle")
        
        db = SessionLocal()
        
        try:
            # Get all unique embassies being monitored
            active_embassies = self._get_active_embassies(db)
            
            if not active_embassies:
                logger.info("No active monitors, skipping cycle")
                return
            
            logger.info(f"Checking {len(active_embassies)} embassies")
            
            for embassy in active_embassies:
                # Skip CUSTOM embassy type - handled separately
                if embassy == EmbassyType.CUSTOM:
                    continue
                    
                # Check if scraper is paused
                if self._is_scraper_paused(db, embassy):
                    logger.info(f"Scraper for {embassy.value} is paused, skipping")
                    self._update_monitors_status(db, embassy, "paused")
                    continue
                
                # Run the scraper
                result = await self._check_embassy(embassy)
                
                # Log the result
                self._log_availability(db, embassy, result)
                
                # Update scraper health
                self._update_scraper_health(db, embassy, result)
                
                # Update monitor status (truncate to 50 chars for DB column)
                if result.success and result.slots_available:
                    check_status = "slots_found"
                elif result.success:
                    check_status = "success"
                else:
                    check_status = f"error: {result.error_message or 'unknown'}"
                check_status = check_status[:50]
                self._update_monitors_status(db, embassy, check_status)
                
                # If slots available, send alerts
                if result.success and result.slots_available:
                    await self._send_alerts_for_embassy(db, embassy, result)
                
                db.commit()
            
            # Handle custom URL monitors
            await self._check_custom_monitors(db)
        
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {str(e)}")
            db.rollback()
        
        finally:
            db.close()
        
        logger.info("Monitoring cycle completed")
    
    def _get_active_embassies(self, db: Session) -> List[EmbassyType]:
        """Get list of embassies with active monitors"""
        monitors = db.query(Monitor).filter(Monitor.is_active == True).all()
        return list(set(m.embassy for m in monitors))
    
    def _update_monitors_status(self, db: Session, embassy: EmbassyType, status: str):
        """Update last_checked_at and last_check_status for all monitors of this embassy"""
        monitors = db.query(Monitor).filter(
            Monitor.embassy == embassy,
            Monitor.is_active == True
        ).all()
        
        now = datetime.utcnow()
        for monitor in monitors:
            monitor.last_checked_at = now
            monitor.last_check_status = status
        
        logger.debug(f"Updated status for {len(monitors)} monitors of {embassy.value}")
    
    async def _check_custom_monitors(self, db: Session):
        """Check all custom URL monitors"""
        custom_monitors = db.query(Monitor).filter(
            Monitor.embassy == EmbassyType.CUSTOM,
            Monitor.is_active == True,
            Monitor.custom_url.isnot(None)
        ).all()
        
        if not custom_monitors:
            return
        
        logger.info(f"Checking {len(custom_monitors)} custom URL monitors")
        
        for monitor in custom_monitors:
            try:
                result = await self._check_custom_url(monitor.custom_url)
                
                # Update monitor status
                now = datetime.utcnow()
                monitor.last_checked_at = now
                
                if result.success:
                    if result.slots_available:
                        monitor.last_check_status = "slots_found"
                        # Send alert for this monitor
                        await self._send_alert_for_custom_monitor(db, monitor, result)
                    else:
                        monitor.last_check_status = "success"
                else:
                    err = result.error_message or 'unknown'
                    monitor.last_check_status = f"error: {err}"[:50]
                
                db.commit()
                
            except Exception as e:
                logger.error(f"Error checking custom monitor {monitor.id}: {str(e)}")
                monitor.last_checked_at = datetime.utcnow()
                monitor.last_check_status = f"error: {str(e)}"[:50]
                db.commit()
    
    async def _send_alert_for_custom_monitor(self, db: Session, monitor: Monitor, result: AvailabilityResult):
        """Send alert for a custom URL monitor"""
        user = monitor.user
        
        if not user:
            return
        
        # Check notification preference
        pref = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user.id
        ).first()
        
        telegram_id = pref.telegram_chat_id if pref else None
        
        if telegram_id:
            message = (
                f"🔔 Custom URL Monitor Alert!\n\n"
                f"📍 URL: {monitor.custom_url}\n"
                f"📝 Potential availability detected\n\n"
                f"Check the page for appointment slots."
            )
            await send_telegram_alert(telegram_id, message)
    
    def _is_scraper_paused(self, db: Session, embassy: EmbassyType) -> bool:
        """Check if scraper is paused due to failures"""
        health = db.query(ScraperHealth).filter(
            ScraperHealth.embassy == embassy
        ).first()
        
        if not health:
            return False
        
        if health.is_paused and health.paused_until:
            if datetime.utcnow() < health.paused_until:
                return True
            else:
                # Pause period over, reset
                health.is_paused = False
                health.consecutive_failures = 0
                db.commit()
                return False
        
        return False
    
    async def _check_embassy(self, embassy: EmbassyType) -> AvailabilityResult:
        """Run scraper for a specific embassy"""
        scraper_class = self.scraper_map.get(embassy)
        
        if not scraper_class:
            logger.error(f"No scraper found for {embassy.value}")
            return AvailabilityResult(
                embassy=embassy.value,
                slots_available=False,
                available_dates=[],
                error_message="No scraper configured",
                success=False
            )
        
        try:
            async with scraper_class() as scraper:
                result = await scraper.check_availability()
                return result
        except Exception as e:
            logger.error(f"Scraper error for {embassy.value}: {str(e)}")
            return AvailabilityResult(
                embassy=embassy.value,
                slots_available=False,
                available_dates=[],
                error_message=str(e),
                success=False
            )
    
    async def _check_custom_url(self, url: str) -> AvailabilityResult:
        """Check a custom URL for appointment availability"""
        import time
        start_time = time.time()
        
        # Keywords that might indicate available appointments
        availability_keywords = [
            "available", "schedule", "book now", "select date",
            "open slot", "appointment available", "slots available",
            "book appointment", "choose date"
        ]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                
                check_duration_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code != 200:
                    return AvailabilityResult(
                        embassy="custom",
                        slots_available=False,
                        available_dates=[],
                        error_message=f"HTTP {response.status_code}",
                        success=False,
                        check_duration_ms=check_duration_ms,
                        raw_response=f"Status: {response.status_code}"
                    )
                
                content = response.text.lower()
                
                # Check for availability keywords
                found_keywords = [kw for kw in availability_keywords if kw in content]
                slots_available = len(found_keywords) > 0
                
                return AvailabilityResult(
                    embassy="custom",
                    slots_available=slots_available,
                    available_dates=[],
                    success=True,
                    check_duration_ms=check_duration_ms,
                    raw_response=f"Page accessible. Keywords found: {found_keywords}" if slots_available else "Page accessible. No availability keywords found."
                )
                
        except Exception as e:
            check_duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Custom URL check error: {str(e)}")
            return AvailabilityResult(
                embassy="custom",
                slots_available=False,
                available_dates=[],
                error_message=str(e),
                success=False,
                check_duration_ms=check_duration_ms
            )
    
    def _log_availability(
        self,
        db: Session,
        embassy: EmbassyType,
        result: AvailabilityResult
    ):
        """Log availability check result to database"""
        log_entry = AvailabilityLog(
            embassy=embassy,
            slots_available=result.slots_available,
            available_dates=result.available_dates,
            raw_response=result.raw_response[:10000] if result.raw_response else None,
            check_duration_ms=result.check_duration_ms,
            error_message=result.error_message,
            success=result.success,
        )
        db.add(log_entry)
    
    def _update_scraper_health(
        self,
        db: Session,
        embassy: EmbassyType,
        result: AvailabilityResult
    ):
        """Update scraper health tracking"""
        health = db.query(ScraperHealth).filter(
            ScraperHealth.embassy == embassy
        ).first()
        
        if not health:
            health = ScraperHealth(
                embassy=embassy,
                total_checks=0,
                total_failures=0,
                consecutive_failures=0
            )
            db.add(health)
        
        health.total_checks = (health.total_checks or 0) + 1
        
        if result.success:
            health.consecutive_failures = 0
            health.last_success_at = datetime.utcnow()
        else:
            health.consecutive_failures = (health.consecutive_failures or 0) + 1
            health.total_failures = (health.total_failures or 0) + 1
            health.last_failure_at = datetime.utcnow()
            health.last_error = result.error_message
            
            # Pause if too many consecutive failures
            if health.consecutive_failures >= settings.MAX_FAILURES_BEFORE_PAUSE:
                health.is_paused = True
                health.paused_until = datetime.utcnow() + timedelta(
                    minutes=settings.BACKOFF_MINUTES
                )
                logger.warning(
                    f"Pausing {embassy.value} scraper for {settings.BACKOFF_MINUTES} minutes "
                    f"after {health.consecutive_failures} failures"
                )
    
    async def _send_alerts_for_embassy(
        self,
        db: Session,
        embassy: EmbassyType,
        result: AvailabilityResult
    ):
        """Send alerts to all users monitoring this embassy"""
        # Get all active monitors for this embassy
        monitors = db.query(Monitor).filter(
            Monitor.embassy == embassy,
            Monitor.is_active == True
        ).all()
        
        logger.info(f"Found {len(monitors)} active monitors for {embassy.value}")
        
        for monitor in monitors:
            user = monitor.user
            
            if not user or not user.is_active:
                continue
            
            # Check date range preference
            if monitor.preferred_date_from or monitor.preferred_date_to:
                filtered_dates = self._filter_dates_by_preference(
                    result.available_dates,
                    monitor.preferred_date_from,
                    monitor.preferred_date_to
                )
                if not filtered_dates:
                    continue  # No dates in user's preferred range
            else:
                filtered_dates = result.available_dates
            
            # Send notification based on preference
            sent = False
            sent_via = user.notification_preference
            
            if user.notification_preference in [NotificationPreference.TELEGRAM, NotificationPreference.BOTH]:
                if user.telegram_chat_id:
                    sent = await send_telegram_alert(
                        chat_id=user.telegram_chat_id,
                        embassy=embassy.value,
                        available_dates=filtered_dates,
                    )
                    if sent:
                        sent_via = NotificationPreference.TELEGRAM
            
            if user.notification_preference in [NotificationPreference.WHATSAPP, NotificationPreference.BOTH]:
                if user.whatsapp_number:
                    whatsapp_sent = await send_whatsapp_alert(
                        to_number=user.whatsapp_number,
                        embassy=embassy.value,
                        available_dates=filtered_dates,
                    )
                    if whatsapp_sent:
                        sent_via = NotificationPreference.WHATSAPP
                        sent = True
            
            # Record the alert
            if sent:
                alert = Alert(
                    user_id=user.id,
                    monitor_id=monitor.id,
                    embassy=embassy,
                    available_dates=filtered_dates,
                    message=f"Slots available at {embassy.value}",
                    sent_via=sent_via,
                    delivered=True,
                )
                db.add(alert)
                logger.info(f"Alert sent to user {user.id} for {embassy.value}")
    
    def _filter_dates_by_preference(
        self,
        dates: List[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> List[str]:
        """Filter available dates by user's preferred date range"""
        if not dates:
            return []
        
        filtered = []
        for date_str in dates:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                
                if date_from and date_obj < date_from:
                    continue
                if date_to and date_obj > date_to:
                    continue
                    
                filtered.append(date_str)
            except ValueError:
                continue
        
        return filtered
    
    async def health_check(self):
        """Periodic health check to monitor scraper status"""
        logger.info("Running scraper health check")
        
        db = SessionLocal()
        
        try:
            healths = db.query(ScraperHealth).all()
            
            for health in healths:
                if health.is_paused:
                    logger.warning(
                        f"{health.embassy.value}: PAUSED until {health.paused_until}"
                    )
                elif health.consecutive_failures > 0:
                    logger.warning(
                        f"{health.embassy.value}: {health.consecutive_failures} consecutive failures"
                    )
                else:
                    logger.info(
                        f"{health.embassy.value}: Healthy - last success {health.last_success_at}"
                    )
        
        finally:
            db.close()


# Global scheduler instance
visa_scheduler = VisaMonitorScheduler()


def start_scheduler():
    """Start the global scheduler"""
    visa_scheduler.start()


def stop_scheduler():
    """Stop the global scheduler"""
    visa_scheduler.stop()
