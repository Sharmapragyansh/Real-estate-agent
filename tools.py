import json
import glob
import os
import asyncio
from typing import Dict, Any, Optional
from db import (
    query_properties, get_property, get_all_properties, 
    insert_lead_booking, row_to_summary
)
from whatsapp import (
    send_text_message, send_image_message, send_video_message
)

current_sender: Optional[str] = None

def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)

def set_current_sender(sender: str):
    global current_sender
    current_sender = sender

def get_matching_properties(bhk: str, budget: str, location: str) -> str:
    rows = query_properties(bhk, budget, location)
    summaries = [row_to_summary(r) for r in rows]
    return json.dumps(summaries)

def format_property_text(prop: Dict[str, Any]) -> str:
    highlights = prop.get("highlights", [])
    if isinstance(highlights, str):
        try:
            highlights = json.loads(highlights)
        except:
            highlights = []
    
    highlights_text = "\n".join([f"✓ {h}" for h in highlights]) if highlights else "N/A"
    
    return f"""*{prop['name']}*
{prop['builder']} | {prop['tag']}

*Configuration:* {prop['bhk']}
*Carpet Area:* {prop['carpet_area']}
*Price:* {prop['price']}
*Location:* {prop['location']}
*Address:* {prop['address']}
*Maps:* {prop['maps_link']}
*Rating:* {prop['rating']}
*Possession:* {prop['possession_status']}

*Highlights:*
{highlights_text}"""

def get_property_details(property_id: str) -> str:
    if not current_sender:
        return "Error: No recipient set"
    
    prop = get_property(property_id)
    if not prop:
        return f"Property {property_id} not found"
    
    _run_async(send_text_message(current_sender, format_property_text(prop)))
    
    media_dir = prop.get("media_dir", "")
    hero_path = os.path.join(media_dir, "hero.jpg")
    if os.path.exists(hero_path):
        _run_async(send_image_message(current_sender, hero_path, f"{prop['name']} - Hero Image"))
    
    photo_count = 0
    for photo in sorted(glob.glob(os.path.join(media_dir, "photo*.jpg"))):
        _run_async(send_image_message(current_sender, photo))
        photo_count += 1
    
    for photo in sorted(glob.glob(os.path.join(media_dir, "photo*.jpeg"))):
        _run_async(send_image_message(current_sender, photo))
        photo_count += 1
    
    for photo in sorted(glob.glob(os.path.join(media_dir, "photo*.png"))):
        _run_async(send_image_message(current_sender, photo))
        photo_count += 1
    
    return f"Sent details and {photo_count + 1} photos for {prop['name']}"

def send_property_video(property_id: str) -> str:
    if not current_sender:
        return "Error: No recipient set"
    
    prop = get_property(property_id)
    if not prop:
        return f"Property {property_id} not found"
    
    media_dir = prop.get("media_dir", "")
    
    for ext in ["mp4", "mov", "avi"]:
        video_path = os.path.join(media_dir, f"walkthrough.{ext}")
        if os.path.exists(video_path):
            _run_async(send_video_message(current_sender, video_path, f"{prop['name']} - Walkthrough Video"))
            return f"Sent walkthrough video for {prop['name']}"
    
    for video in glob.glob(os.path.join(media_dir, "*.mp4")):
        _run_async(send_video_message(current_sender, video, f"{prop['name']} - Video"))
        return f"Sent video for {prop['name']}"
    
    return f"No walkthrough video found for {prop['name']}"

def book_site_visit(property_id: str, visit_datetime_iso: str, visit_display: str) -> str:
    if not current_sender:
        return "Error: No recipient set"
    
    prop = get_property(property_id)
    if not prop:
        return f"Property {property_id} not found"
    
    insert_lead_booking(current_sender, property_id, visit_datetime_iso, visit_display)
    
    return f"Booked visit for {visit_display} at {prop['name']}"

TOOLS = [
    {
        "name": "get_matching_properties",
        "description": "Return properties matching the lead's stated preferences.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bhk": {"type": "string", "description": "BHK configuration (e.g., '2 BHK', '3 BHK', 'any')"},
                "budget": {"type": "string", "description": "Budget range (e.g., '1 Cr', '2-3 Cr', 'any')"},
                "location": {"type": "string", "description": "Preferred location (e.g., 'Gurgaon', 'Bangalore', 'any')"}
            },
            "required": ["bhk", "budget", "location"]
        }
    },
    {
        "name": "get_property_details",
        "description": "Send full details plus a photo gallery for one property directly to the user on WhatsApp.",
        "input_schema": {
            "type": "object",
            "properties": {"property_id": {"type": "string"}},
            "required": ["property_id"]
        }
    },
    {
        "name": "send_property_video",
        "description": "Send the walkthrough video for one property directly to the user on WhatsApp.",
        "input_schema": {
            "type": "object",
            "properties": {"property_id": {"type": "string"}},
            "required": ["property_id"]
        }
    },
    {
        "name": "book_site_visit",
        "description": "Record a site visit booking and schedule a reminder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "property_id": {"type": "string"},
                "visit_datetime_iso": {"type": "string", "description": "ISO 8601 datetime (e.g., '2026-09-20T15:00:00')"},
                "visit_display": {"type": "string", "description": "Human-friendly label, e.g. 'Sunday 3 PM'"}
            },
            "required": ["property_id", "visit_datetime_iso", "visit_display"]
        }
    }
]

def dispatch_tool(name: str, input_params: Dict[str, Any]) -> str:
    tool_map = {
        "get_matching_properties": get_matching_properties,
        "get_property_details": get_property_details,
        "send_property_video": send_property_video,
        "book_site_visit": book_site_visit,
    }
    
    if name not in tool_map:
        return f"Error: Unknown tool {name}"
    
    try:
        return tool_map[name](**input_params)
    except Exception as e:
        return f"Error executing {name}: {str(e)}"