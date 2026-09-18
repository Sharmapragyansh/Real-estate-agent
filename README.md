# WhatsApp Real Estate Lead Agent

An agentic WhatsApp chatbot for real estate lead qualification built with:
- **FastAPI** - Web framework
- **Anthropic Claude** - LLM with tool-use
- **Meta WhatsApp Cloud API** - Messaging
- **SQLite** - Database
- **APScheduler** - Reminder scheduling

## Features

- Autonomous tool-use agent (no fixed decision trees)
- Handles Hindi/English/Hinglish mixed input
- Property search with BHK, budget, location filters
- Sends property details, photos, and walkthrough videos
- Books site visits with natural language date parsing
- Automated visit reminders

## Project Structure

```
whatsapp-agent/
├── app.py                 # FastAPI entrypoint with webhook endpoints
├── agent.py               # Claude tool-use loop
├── tools.py               # Tool implementations
├── whatsapp.py            # Meta Cloud API client
├── db.py                  # SQLite schema + data access
├── properties_seed.py     # Static property catalog
├── test_implementation.py # Test script
├── media/                 # Property media (photos, videos)
│   └── <property_slug>/
│       ├── hero.jpg
│       ├── photo1.jpg
│       └── walkthrough.mp4
├── .env                   # Environment variables
└── requirements.txt       # Python dependencies
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   Copy `.env` and fill in your credentials:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-...
   WHATSAPP_TOKEN=EAAG...
   PHONE_NUMBER_ID=...
   WABA_ID=...
   VERIFY_TOKEN=your_arbitrary_string
   REMINDER_DELAY_SECONDS=20  # Use 86400 for 24 hours in production
   MODEL=claude-3-5-sonnet-20241022
   ```

3. **Get WhatsApp Business API credentials:**
   - Create a Meta Business App at developers.facebook.com
   - Add WhatsApp product
   - Note PHONE_NUMBER_ID and WABA_ID
   - Generate access token
   - Add your phone as test recipient

4. **Run locally with Cloudflare Tunnel:**
   ```bash
   # Terminal 1
   uvicorn app:app --reload --port 8000
   
   # Terminal 2
   cloudflared tunnel --url http://localhost:8000
   ```
   
   Use the `https://*.trycloudflare.com/webhook` URL in Meta Dashboard > WhatsApp > Configuration > Callback URL

5. **Subscribe to messages:**
   ```bash
   curl -X POST https://your-domain.com/test/subscribe
   ```

## Running Tests

```bash
python test_implementation.py
```

## API Endpoints

- `GET /webhook` - Meta verification handshake
- `POST /webhook` - Incoming WhatsApp messages
- `GET /health` - Health check
- `POST /test/subscribe` - Subscribe app to WABA events

## Deployment (Railway)

1. Push to GitHub
2. Connect to Railway
3. Set environment variables
4. Add PostgreSQL for persistent storage
5. Update webhook URL in Meta Dashboard
6. Re-run subscription

## Cost Estimate (Monthly)

| Component | Cost |
|-----------|------|
| Hosting (Railway) | $5-15 |
| Claude API | $25-125 (500 conversations) |
| WhatsApp Messages | $0-50+ |
| **Total** | **~$30-75** |

## Key Files

- **db.py**: SQLite operations, session management, deduplication
- **agent.py**: Anthropic tool-use loop with conversation history
- **tools.py**: Four tools - property search, details, video, booking
- **whatsapp.py**: Media upload, message sending, app subscription
- **app.py**: FastAPI webhook handlers, scheduler for reminders

## Adding Properties

Edit `properties_seed.py` and add entries to the `PROPERTIES` list. Media goes in `media/<property_slug>/`.

Required media files:
- `hero.jpg` - Main property image
- `photo*.jpg` - Gallery photos
- `walkthrough.mp4` - Video tour (< 16MB)

## Operational Notes

- Dev tokens expire every 24 hours - use system-user token for production
- Re-run `/subscribed_apps` after any app changes
- Verify media delivery on real device (HTTP 200 ≠ delivered)
- Message deduplication prevents double-processing
- Plan for context window management in long conversations