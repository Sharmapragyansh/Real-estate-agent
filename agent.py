import os
import json
from typing import List, Dict, Any
import anthropic
from dotenv import load_dotenv
from db import load_session, save_session, get_lead_by_phone
from tools import dispatch_tool, set_current_sender, TOOLS

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = os.environ.get("MODEL", "claude-3-5-sonnet-latest")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a WhatsApp lead-qualification agent for a real estate brokerage.

- Greet the lead using their name and any preferences already on file.
- Ask about BHK configuration, budget, and preferred location if not already known.
- Use get_matching_properties to fetch listings; never invent property data yourself.
- When a lead wants more on a specific property, call get_property_details or send_property_video; do not describe photos or attach media yourself, the tool sends media directly.
- Users may write in Hindi, English, or mixed Hinglish (e.g. "sunday ko 3pm visit kar sakta hu kya"). Parse the intent and datetime, then call book_site_visit with visit_datetime_iso in ISO 8601 and a human-friendly visit_display.
- Keep responses short and conversational, suited to a WhatsApp thread.
- If the user says "hi", "hello", or similar greeting, greet them back and ask about their preferences.
- For Hinglish date parsing: "sunday" = next Sunday, "kal" = tomorrow, "parso" = day after tomorrow, "3pm" = 15:00, "shaam 5 baje" = 17:00, "subah 10 baje" = 10:00."""

def _to_sdk_message(role: str, content) -> Dict[str, Any]:
    if role == "user" and isinstance(content, list):
        # Tool results from our system
        sdk_content = []
        for item in content:
            if item.get("type") == "tool_result":
                sdk_content.append({
                    "type": "tool_result",
                    "tool_use_id": item["tool_use_id"],
                    "content": str(item.get("content", ""))
                })
        return {"role": "user", "content": sdk_content}
    elif role == "assistant" and isinstance(content, list):
        # Assistant messages with tool_use
        sdk_content = []
        for item in content:
            if item.get("type") == "text":
                sdk_content.append({"type": "text", "text": item.get("text", "")})
            elif item.get("type") == "tool_use":
                sdk_content.append({
                    "type": "tool_use",
                    "id": item["id"],
                    "name": item["name"],
                    "input": item["input"]
                })
        return {"role": "assistant", "content": sdk_content}
    else:
        # Plain text message
        return {"role": role, "content": str(content)}

def _normalize_history(history: List[Dict]) -> List[Dict]:
    result = []
    for msg in history:
        content = msg.get("content", "")
        if isinstance(content, str):
            result.append({"role": msg["role"], "content": content})
        elif isinstance(content, list):
            # Check if it's tool results or assistant with tools
            if msg["role"] == "user" and content and content[0].get("type") == "tool_result":
                result.append(_to_sdk_message("user", content))
            elif msg["role"] == "assistant":
                result.append(_to_sdk_message("assistant", content))
            else:
                # Plain text in list format
                text = " ".join(item.get("text", "") for item in content if item.get("type") == "text")
                result.append({"role": msg["role"], "content": text})
    return result

async def run_agent_turn(phone_number: str, user_text: str) -> str:
    set_current_sender(phone_number)
    
    history = load_session(phone_number)
    lead = get_lead_by_phone(phone_number)
    
    if lead:
        context = f"\n\n[Lead Info: Name: {lead.get('name') or 'Unknown'}, BHK: {lead.get('bhk_pref') or 'Not specified'}, Budget: {lead.get('budget_pref') or 'Not specified'}, Location: {lead.get('location_pref') or 'Not specified'}]"
    else:
        context = "\n\n[Lead Info: New lead, no preferences captured yet]"
    
    messages = _normalize_history(history)
    messages.append({"role": "user", "content": user_text + context})
    
    while True:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
            max_tokens=1024
        )
        
        if response.stop_reason != "tool_use":
            final_text = "".join(b.text for b in response.content if b.type == "text")
            # Save as plain text for simplicity
            messages.append({"role": "assistant", "content": final_text})
            save_session(phone_number, messages)
            return final_text
        
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = dispatch_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })
        
        # Add assistant message with tool_use
        messages.append({
            "role": "assistant", 
            "content": [
                {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
                for b in response.content if b.type == "tool_use"
            ]
        })
        # Add tool results as user message
        messages.append({"role": "user", "content": tool_results})