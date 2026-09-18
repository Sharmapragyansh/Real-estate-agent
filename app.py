import os
import json
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

from db import init_db, seed_properties, already_processed, mark_processed, get_property
from properties_seed import get_properties
from agent import run_agent_turn
from whatsapp import send_text_message, subscribe_app, whatsapp_client
from tools import set_current_sender

scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_properties(get_properties())
    
    for prop in get_properties():
        media_dir = prop.get("media_dir", "")
        os.makedirs(media_dir, exist_ok=True)
    
    scheduler.start()
    
    try:
        await subscribe_app()
        print("WhatsApp app subscribed successfully")
    except Exception as e:
        print(f"Warning: Could not subscribe app: {e}")
    
    yield
    
    scheduler.shutdown()
    await whatsapp_client.close()

app = FastAPI(title="WhatsApp Real Estate Agent", lifespan=lifespan)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "your_own_arbitrary_string")
REMINDER_DELAY_SECONDS = int(os.environ.get("REMINDER_DELAY_SECONDS", "20"))

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def receive_webhook(request: Request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"status": "invalid_json"}, status_code=400)
    
    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages", [])
        
        if not messages:
            return {"status": "no_messages"}
        
        message = messages[0]
        message_id = message["id"]
        sender = message["from"]
        text = message.get("text", {}).get("body", "")
        
    except (KeyError, IndexError):
        return {"status": "ignored"}
    
    if already_processed(message_id):
        return {"status": "duplicate"}
    
    mark_processed(message_id)
    
    try:
        reply = await run_agent_turn(sender, text)
        if reply:
            await send_text_message(sender, reply)
    except Exception as e:
        print(f"Error processing message: {e}")
        await send_text_message(sender, "Sorry, I encountered an error. Please try again.")
    
    return {"status": "ok"}

def schedule_reminder(recipient: str, property_id: str, visit_display: str):
    delay = REMINDER_DELAY_SECONDS
    run_at = datetime.now() + timedelta(seconds=delay)
    scheduler.add_job(send_reminder, "date", run_date=run_at,
                      args=[recipient, property_id, visit_display])

def send_reminder(recipient: str, property_id: str, visit_display: str):
    import asyncio
    try:
        prop = get_property(property_id)
        if prop:
            text = f"⏰ Reminder: Your visit to {prop['name']} is coming up ({visit_display}).\n📍 {prop['address']}\n🗺️ {prop['maps_link']}"
            asyncio.run(send_text_message(recipient, text))
    except Exception as e:
        print(f"Error sending reminder: {e}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/test/subscribe")
async def test_subscribe():
    try:
        result = await subscribe_app()
        return {"status": "subscribed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)