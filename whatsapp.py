import os
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
API_VERSION = "v25.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}"

HEADERS = {
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json"
}

class WhatsAppClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def send_text_message(self, recipient: str, text: str) -> dict:
        url = f"{BASE_URL}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": text}
        }
        response = await self.client.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def upload_media(self, file_path: str, media_type: str) -> str:
        url = f"{BASE_URL}/media"
        
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, media_type)}
            data = {
                "messaging_product": "whatsapp",
                "type": media_type.split("/")[0]
            }
            
            upload_headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
            response = await self.client.post(url, headers=upload_headers, data=data, files=files)
            response.raise_for_status()
            return response.json()["id"]
    
    async def send_media_message(self, recipient: str, media_id: str, kind: str, caption: Optional[str] = None) -> dict:
        url = f"{BASE_URL}/messages"
        
        media_obj = {"id": media_id}
        if caption:
            media_obj["caption"] = caption
        
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": kind,
            kind: media_obj
        }
        
        response = await self.client.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def send_image(self, recipient: str, file_path: str, caption: Optional[str] = None) -> dict:
        media_id = await self.upload_media(file_path, "image/jpeg")
        return await self.send_media_message(recipient, media_id, "image", caption)
    
    async def send_video(self, recipient: str, file_path: str, caption: Optional[str] = None) -> dict:
        media_id = await self.upload_media(file_path, "video/mp4")
        return await self.send_media_message(recipient, media_id, "video", caption)
    
    async def send_document(self, recipient: str, file_path: str, caption: Optional[str] = None, filename: Optional[str] = None) -> dict:
        media_id = await self.upload_media(file_path, "application/pdf")
        url = f"{BASE_URL}/messages"
        
        doc_obj = {"id": media_id}
        if caption:
            doc_obj["caption"] = caption
        if filename:
            doc_obj["filename"] = filename
        
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "document",
            "document": doc_obj
        }
        
        response = await self.client.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()

whatsapp_client = WhatsAppClient()

async def send_text_message(recipient: str, text: str) -> dict:
    return await whatsapp_client.send_text_message(recipient, text)

async def send_image_message(recipient: str, file_path: str, caption: Optional[str] = None) -> dict:
    return await whatsapp_client.send_image(recipient, file_path, caption)

async def send_video_message(recipient: str, file_path: str, caption: Optional[str] = None) -> dict:
    return await whatsapp_client.send_video(recipient, file_path, caption)

async def send_document_message(recipient: str, file_path: str, caption: Optional[str] = None, filename: Optional[str] = None) -> dict:
    return await whatsapp_client.send_document(recipient, file_path, caption, filename)

async def subscribe_app():
    import os
    WABA_ID = os.environ.get("WABA_ID")
    WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
    
    if not WABA_ID or not WHATSAPP_TOKEN:
        raise ValueError("WABA_ID and WHATSAPP_TOKEN must be set in environment")
    
    url = f"https://graph.facebook.com/{API_VERSION}/{WABA_ID}/subscribed_apps"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers)
        resp.raise_for_status()
        return resp.json()