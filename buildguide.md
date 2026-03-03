# Visa Appointment Monitor — Product Specification & Build Guide

## What It Is
A notification tool that monitors embassy appointment availability and sends instant alerts when a slot opens. Monitor only — no auto-booking. Users get the alert and book manually themselves.

**Core philosophy:** People manually refresh embassy websites for hours every day. This tool does that automatically and interrupts them only when a slot is available.

---

## Target Market
- **Primary:** Ghana — US, UK, Schengen visa applicants
- **Expansion:** Nigeria, Kenya, India, Pakistan (all high demand, long wait times)
- **B2B angle:** Visa agents and immigration consultants who handle multiple clients

---

## Legal Position (Important)

### What is LEGAL ✅
- Monitoring publicly visible appointment availability pages
- Sending notifications to users when slots appear
- User manually logs in and books the slot themselves
- Checking at reasonable intervals (not aggressive scraping)

### What is RISKY ❌
- Auto-logging into embassy portals on behalf of users(DO NOT DO THIS)
- Auto-booking appointments without human confirmation(DO NOT DO THIS)
- Bypassing CAPTCHAs(if present on availability pages) (DO NOT DO THIS)
- Running headless browsers too aggressively(Add random delays, rotate user agents)
- Simulating human clicks to beat bot detection(Use stealth mode, but be cautious)

### Safe Design Rule
**Your bot never touches the user's account. It only watches public availability pages and tells the user when to act.**

---

## How It Works (User Flow)

```
User signs up and sets preferences
    ↓
Selects embassy (US, UK, Schengen, etc.)
    ↓
Selects visa type and preferred date range
    ↓
Enters their Telegram or WhatsApp number
    ↓
Monitor runs in background checking availability page
    ↓
Slot appears on embassy website
    ↓
User gets instant Telegram/WhatsApp alert
    ↓
User logs in manually and books the slot themselves
    ↓
User marks alert as "booked" to stop notifications
```

---

## Tech Stack

### Backend (Python)
- **Framework:** FastAPI
- **Scraping:** Playwright (headless Chromium) or Requests + BeautifulSoup
- **Task Scheduler:** APScheduler or Celery + Redis
- **Database:** PostgreSQL (users, preferences, alert history)
- **Notifications:** Telegram Bot API (free, instant) + Twilio for WhatsApp
- **Proxy Rotation:** Residential proxies (Bright Data or Oxylabs) to avoid IP blocks
- **Hosting:** Railway or DigitalOcean (needs always-on server)

### Frontend (React/TypeScript)
- **Framework:** Next.js
- **Hosting:** Vercel

### Monitoring Approach
- Check embassy availability page every 3-10 minutes (not too aggressive)
- Use rotating user agents to appear as normal browser traffic
- Add random delays between checks (2-8 seconds)
- If blocked, back off for 30 minutes then retry

---

## Embassies to Monitor (Start Small)

### Phase 1 — Ghana Focus
| Embassy | URL Pattern | Difficulty |
|---------|-------------|-----------|
| US Embassy Accra | ustraveldocs.com | Medium |
| UK Visa (VFS Global) | vfsglobal.com | Medium |
| Schengen (various) | Various VFS/TLScontact | Hard |

### Phase 2 — West Africa Expansion
- Nigeria (Lagos, Abuja)
- Kenya (Nairobi)
- Senegal (Dakar)

---

## Database Schema

```sql
-- Users
users (
  id, email, phone, telegram_chat_id,
  notification_preference, created_at, plan
)

-- Monitor preferences
monitors (
  id, user_id, embassy, visa_type,
  preferred_date_from, preferred_date_to,
  is_active, created_at
)

-- Availability checks
availability_logs (
  id, embassy, checked_at, slots_available,
  raw_response
)

-- Alerts sent
alerts (
  id, user_id, monitor_id, embassy,
  slot_date, message, sent_at, booked
)
```

---

## Build Phases

### Phase 1 — Core Monitor (Weeks 1-3)
**Goal:** Working monitor for one embassy

- [ ] Set up FastAPI backend
- [ ] Set up PostgreSQL database
- [ ] Research US Embassy Accra appointment page structure
- [ ] Build scraper for availability page (Playwright)
- [ ] Implement check scheduler (every 5 minutes)
- [ ] Set up Telegram Bot (free, easiest to start)
- [ ] Build alert sending function
- [ ] Test end to end — scraper detects slot → Telegram message sent
- [ ] Deploy to Railway (always-on server required)
- [ ] Manual testing with real embassy page

**Deliverable:** Bot that monitors one embassy and sends Telegram alerts

---

### Phase 2 — User System & More Embassies (Weeks 4-6)
**Goal:** Multiple users, multiple embassies

- [ ] Build user registration and login
- [ ] Build monitor preference settings (embassy, visa type, date range)
- [ ] Build simple frontend (Next.js) for user setup
- [ ] Add UK Visa (VFS Global) scraper
- [ ] Add Schengen visa scraper (at least one country)
- [ ] Add WhatsApp alerts via Twilio
- [ ] Build proxy rotation to avoid IP blocks
- [ ] Add random delay logic between checks
- [ ] Build alert history page for users
- [ ] Test with multiple users simultaneously

**Deliverable:** Multi-user, multi-embassy platform

---

### Phase 3 — Monetise & Launch (Weeks 7-10)
**Goal:** First paying users

- [ ] Build pricing tiers (Free and Pro)
- [ ] Integrate Stripe for payments
- [ ] Free tier: 1 embassy, Telegram alerts, 10-minute checks
- [ ] Pro tier: multiple embassies, WhatsApp + Telegram, 3-minute checks
- [ ] Add B2B tier for visa agents (multiple client monitors)
- [ ] Build agent dashboard (monitor multiple clients from one account)
- [ ] Launch to your friend's visa agent network in Ghana
- [ ] Expand to Nigerian visa agent communities
- [ ] List on relevant directories

**Deliverable:** Paying users from Ghana visa agent network

---

## Pricing Model

| Plan | Price | Features |
|------|-------|---------|
| Free | $0 | 1 embassy, Telegram only, 10-min checks |
| Pro | $15/month | 3 embassies, WhatsApp + Telegram, 3-min checks |
| Agent | $49/month | Unlimited clients, priority checks, dashboard |

**B2B note:** Visa agents will pay $49/month easily because they charge clients $50-200 per successful booking. The ROI is immediate.

---

## Key Technical Challenges

### 1. Embassy Website Changes
Embassy portals update their structure regularly. When they do, your scraper breaks.

**Solution:**
- Monitor scraper health daily
- Alert yourself (not users) when scraper fails
- Build scraper in modular way so each embassy is a separate module
- Have fallback: if scraper fails 3 times in a row, pause that embassy and notify users

### 2. IP Blocking
Embassies and their booking systems (VFS, BLS) actively block scraper IPs.

**Solution:**
- Use residential proxy rotation from day one
- Check at reasonable intervals (3-10 minutes, not every 30 seconds)
- Randomise check intervals slightly
- Rotate user agents with each request
- Use Playwright with stealth mode plugin

### 3. CAPTCHA
Some booking systems use CAPTCHA on availability pages.

**Solution:**
- If CAPTCHA appears on public availability page — that embassy is not scrapable safely
- Avoid those embassies or wait for official API
- Focus on VFS Global which shows availability without CAPTCHA on public pages

### 4. Legal Exposure
**Mitigation:**
- Never store user login credentials
- Never access user accounts
- Only monitor public availability pages
- Clear terms of service stating you only monitor and notify
- User is responsible for their own booking

---

## Anti-Detection Configuration

```python
# Playwright stealth configuration
from playwright.async_api import async_playwright

async def create_stealth_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        return context
```

---

## Telegram Bot Setup (Free & Fast)

```python
import telegram

async def send_alert(chat_id: str, embassy: str, slot_date: str):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    message = f"""
🚨 APPOINTMENT SLOT AVAILABLE

Embassy: {embassy}
Date: {slot_date}

Book NOW before it's taken:
👉 [Booking link]

Reply /booked when done to stop alerts.
    """
    await bot.send_message(chat_id=chat_id, text=message)
```

---

## B2B Agent Dashboard Features

For your friend and other visa agents:
- One login, multiple client profiles
- Each client has their own embassy preferences
- Agent sees all alerts in one dashboard
- Bulk notification when multiple slots open
- Client management (add/remove clients)
- Monthly report of successful bookings

---

## Go-To-Market Strategy

### Step 1 — Your Friend's Network (Week 1)
- Build prod ready version for one embassy
- Give your friend free access
- He uses it with his existing clients
- Collect feedback and testimonials

### Step 2 — Ghana Visa Agent Community (Month 2)
- Your friend introduces you to other agents
- Word of mouth in a tight community
- Agents pay $49/month, each serves 10-50 clients
- 10 agents = $490/month

### Step 3 — Direct to Applicants (Month 3+)
- WhatsApp groups for people waiting on US/UK visas in Ghana
- People in these groups are desperate and will pay
- $15/month to never miss a slot is obvious value

### Step 4 — West Africa Expansion
- Nigeria has 200M people, massive visa demand
- Same product, add Nigerian embassies
- Partner with Nigerian visa agents

---


---

## Resources

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Playwright Python](https://playwright.dev/python/)
- [Playwright Stealth](https://github.com/AtuboDad/playwright_stealth)
- [Twilio WhatsApp](https://www.twilio.com/whatsapp)
- [VFS Global](https://www.vfsglobal.com)
- [US Travel Docs](https://www.ustraveldocs.com)

---