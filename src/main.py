"""
Visa Monitor Bot - FastAPI Application
Main entry point for the API server
"""
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .database import init_db, close_db
from .api.routes.users import router as users_router
from .api.routes.monitors import router as monitors_router
from .api.routes.alerts import router as alerts_router
from .scheduler.monitor import start_scheduler, stop_scheduler
from .notifications.telegram_bot import telegram_notifier

# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Startup: Initialize database, start scheduler
    Shutdown: Stop scheduler, close connections
    """
    import os
    
    # Startup
    logger.info("Starting Visa Monitor Bot...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize Telegram bot
    try:
        await telegram_notifier.initialize()
        logger.info("Telegram bot initialized")
        
        # Auto-setup webhook if running on Render
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_url:
            webhook_url = f"{render_url}/api/v1/telegram/webhook"
            success = await telegram_notifier.set_webhook(webhook_url)
            if success:
                logger.info(f"Telegram webhook auto-configured: {webhook_url}")
            else:
                logger.warning("Failed to auto-configure Telegram webhook")
    except Exception as e:
        logger.warning(f"Failed to initialize Telegram bot: {e}")
    
    # Start the monitoring scheduler
    start_scheduler()
    logger.info("Monitoring scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Visa Monitor Bot...")
    
    stop_scheduler()
    await close_db()
    
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Visa Monitor Bot API",
    description="""
    Monitor visa appointment availability and get instant alerts.
    
    ## Features
    - Monitor multiple embassies (US, UK, Schengen)
    - Instant Telegram and WhatsApp notifications
    - User preference management
    - Alert history tracking
    
    ## How It Works
    1. Create an account and set up your Telegram
    2. Add monitors for the embassies you want to track
    3. Receive instant alerts when slots become available
    4. Book your appointment manually
    5. Mark as booked to stop alerts
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users_router, prefix="/api/v1")
app.include_router(monitors_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
async def root():
    """Serve the frontend UI"""
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "visa-monitor-bot",
    }


@app.post("/api/v1/telegram/webhook")
async def telegram_webhook(request: Request):
    """Webhook endpoint for Telegram bot updates"""
    try:
        update_data = await request.json()
        await telegram_notifier.process_update(update_data)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return {"ok": False}


@app.get("/api/v1/telegram/setup-webhook")
async def setup_telegram_webhook():
    """Setup the Telegram webhook (call once after deployment)"""
    # Get the app URL from environment or construct it
    import os
    app_url = os.environ.get("RENDER_EXTERNAL_URL", "https://visamonitor.onrender.com")
    webhook_url = f"{app_url}/api/v1/telegram/webhook"
    
    success = await telegram_notifier.set_webhook(webhook_url)
    if success:
        return {"status": "success", "webhook_url": webhook_url}
    else:
        return {"status": "failed", "message": "Failed to set webhook"}


@app.get("/api/v1/embassies")
async def list_embassies():
    """List available embassies to monitor"""
    return {
        "embassies": [
            {
                "id": "us_accra",
                "name": "US Embassy Accra",
                "country": "Ghana",
                "status": "active"
            },
            {
                "id": "us_lagos",
                "name": "US Embassy Lagos",
                "country": "Nigeria",
                "status": "active"
            },
            {
                "id": "uk_vfs_accra",
                "name": "UK Visa (VFS Accra)",
                "country": "Ghana",
                "status": "active"
            },
            {
                "id": "uk_vfs_lagos",
                "name": "UK Visa (VFS Lagos)",
                "country": "Nigeria",
                "status": "active"
            },
            {
                "id": "schengen_accra",
                "name": "Schengen Visa (Accra)",
                "country": "Ghana",
                "status": "active"
            },
        ]
    }
