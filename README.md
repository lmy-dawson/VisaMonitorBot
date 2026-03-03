# Visa Monitor Bot

A notification tool that monitors embassy visa appointment availability and sends instant alerts when slots open.

## Features

- 🔍 **Automated Monitoring**: Checks embassy appointment pages every 5 minutes
- 📱 **Instant Alerts**: Telegram and WhatsApp notifications
- 🏛️ **Multiple Embassies**: US, UK, Schengen visa support
- 🔒 **Privacy First**: Never accesses user accounts, only monitors public pages
- 📊 **Alert History**: Track all notifications and booking status

## Supported Embassies

| Embassy | Location | Status |
|---------|----------|--------|
| US Embassy | Accra, Ghana | ✅ Active |
| US Embassy | Lagos, Nigeria | ✅ Active |
| UK Visa (VFS Global) | Accra, Ghana | ✅ Active |
| UK Visa (VFS Global) | Lagos, Nigeria | ✅ Active |
| Schengen Visa | Accra, Ghana | ✅ Active |

## Quick Start

### 1. Clone and Install

```bash
cd VisaMonitorBot
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required settings:
- `TELEGRAM_BOT_TOKEN`: Get from [@BotFather](https://t.me/botfather)
- `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`

Optional:
- `TWILIO_*`: For WhatsApp notifications
- `PROXY_URL`: For proxy rotation

### 3. Setup Database

The bot uses SQLite by default (no setup required). Initialize the database:

```bash
python scripts/init_db.py
```

This creates `visa_monitor.db` in the project folder. You can view/edit it with [DB Browser for SQLite](https://sqlitebrowser.org/).

### 4. Run the Application

```bash
# Development
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Access the API

- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## API Endpoints

### Authentication
- `POST /api/v1/users/register` - Create account
- `POST /api/v1/users/login` - Get JWT token
- `GET /api/v1/users/me` - Get profile
- `POST /api/v1/users/telegram/setup` - Connect Telegram

### Monitors
- `GET /api/v1/monitors` - List your monitors
- `POST /api/v1/monitors` - Create a monitor
- `PATCH /api/v1/monitors/{id}` - Update monitor
- `DELETE /api/v1/monitors/{id}` - Delete monitor
- `POST /api/v1/monitors/{id}/pause` - Pause monitoring
- `POST /api/v1/monitors/{id}/resume` - Resume monitoring

### Alerts
- `GET /api/v1/alerts` - List your alerts
- `PATCH /api/v1/alerts/{id}/booked` - Mark as booked

## Telegram Bot Setup

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token to your `.env` file
4. Start a chat with your bot
5. Send `/start` to get your chat ID
6. Add the chat ID to your account via the API

## Pricing Tiers

| Plan | Price | Features |
|------|-------|---------|
| Free | $0 | 1 embassy, Telegram only, 10-min checks |
| Pro | $15/month | 3 embassies, WhatsApp + Telegram, 3-min checks |
| Agent | $49/month | Unlimited clients, priority checks, dashboard |

## Project Structure

```
VisaMonitorBot/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── api/
│   │   ├── deps.py          # Dependencies
│   │   └── routes/          # API endpoints
│   ├── scrapers/
│   │   ├── stealth.py       # Anti-detection browser
│   │   ├── base.py          # Base scraper class
│   │   ├── us_embassy.py    # US Embassy scraper
│   │   ├── uk_vfs.py        # UK VFS scraper
│   │   └── schengen.py      # Schengen scraper
│   ├── notifications/
│   │   ├── telegram_bot.py  # Telegram alerts
│   │   └── whatsapp.py      # WhatsApp alerts
│   └── scheduler/
│       └── monitor.py       # APScheduler jobs
├── requirements.txt
├── .env.example
└── README.md
```

## Legal Notice

This tool:
- ✅ Only monitors publicly visible appointment pages
- ✅ Sends notifications to users about availability
- ✅ Users book appointments manually themselves
- ❌ Never accesses user embassy accounts
- ❌ Never auto-books appointments
- ❌ Never stores user embassy credentials

## Development

```bash
# Run tests
pytest

# Format code
black src/
isort src/

# Type checking
mypy src/
```

## Deployment

### Local Development

The default SQLite setup works great for development and small deployments.

### Production (Railway/Docker)

For production with multiple workers, switch to PostgreSQL:

1. Update `.env`: `DATABASE_URL=postgresql://user:pass@host:5432/visa_monitor`
2. Install PostgreSQL driver: `pip install asyncpg psycopg2-binary`
3. Deploy!

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium --with-deps

COPY . .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## License

MIT License - See LICENSE file for details.
