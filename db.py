import sqlite3
import json
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.environ.get("DATABASE_PATH", "sqlite.db")

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id TEXT PRIMARY KEY,
                name TEXT,
                builder TEXT,
                bhk TEXT,
                carpet_area TEXT,
                price TEXT,
                location TEXT,
                address TEXT,
                maps_link TEXT,
                rating TEXT,
                tag TEXT,
                highlights TEXT,
                possession_status TEXT,
                media_dir TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                phone_number TEXT PRIMARY KEY,
                history TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT,
                name TEXT,
                bhk_pref TEXT,
                budget_pref TEXT,
                location_pref TEXT,
                interested_property_id TEXT,
                visit_datetime_iso TEXT,
                visit_display TEXT,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                message_id TEXT PRIMARY KEY,
                processed_at TEXT
            )
        """)
        
        conn.commit()

def seed_properties(properties: List[Dict[str, Any]]):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for prop in properties:
            cursor.execute("""
                INSERT OR REPLACE INTO properties 
                (id, name, builder, bhk, carpet_area, price, location, address, maps_link, rating, tag, highlights, possession_status, media_dir)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prop["id"], prop["name"], prop["builder"], prop["bhk"],
                prop["carpet_area"], prop["price"], prop["location"],
                prop["address"], prop["maps_link"], prop["rating"],
                prop["tag"], json.dumps(prop["highlights"]),
                prop["possession_status"], prop["media_dir"]
            ))
        conn.commit()

def query_properties(bhk: str, budget: str, location: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM properties WHERE 1=1"
        params = []
        
        if bhk and bhk.lower() != "any":
            query += " AND bhk LIKE ?"
            params.append(f"%{bhk}%")
        
        if budget and budget.lower() != "any":
            query += " AND price LIKE ?"
            params.append(f"%{budget}%")
        
        if location and location.lower() != "any":
            query += " AND location LIKE ?"
            params.append(f"%{location}%")
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]

def get_property(property_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM properties WHERE id = ?", (property_id,))
        row = cursor.fetchone()
        if row:
            prop = dict(row)
            prop["highlights"] = json.loads(prop["highlights"]) if prop["highlights"] else []
            return prop
        return None

def get_all_properties() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM properties")
        rows = cursor.fetchall()
        props = []
        for row in rows:
            prop = dict(row)
            prop["highlights"] = json.loads(prop["highlights"]) if prop["highlights"] else []
            props.append(prop)
        return props

def load_session(phone_number: str) -> List[Dict[str, str]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT history FROM sessions WHERE phone_number = ?", (phone_number,))
        row = cursor.fetchone()
        if row and row["history"]:
            return json.loads(row["history"])
        return []

def save_session(phone_number: str, history: List[Dict[str, str]]):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (phone_number, history)
            VALUES (?, ?)
        """, (phone_number, json.dumps(history)))
        conn.commit()

def insert_lead_booking(phone_number: str, property_id: str, visit_datetime_iso: str, visit_display: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO leads (phone_number, interested_property_id, visit_datetime_iso, visit_display, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (phone_number, property_id, visit_datetime_iso, visit_display, datetime.now().isoformat()))
        conn.commit()

def get_lead_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM leads WHERE phone_number = ? ORDER BY created_at DESC LIMIT 1", (phone_number,))
        row = cursor.fetchone()
        return dict(row) if row else None

def already_processed(message_id: str) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM processed_messages WHERE message_id = ?", (message_id,))
        return cursor.fetchone() is not None

def mark_processed(message_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO processed_messages (message_id, processed_at) VALUES (?, ?)",
                      (message_id, datetime.now().isoformat()))
        conn.commit()

def row_to_summary(row: Dict[str, Any]) -> Dict[str, str]:
    return {
        "id": row["id"],
        "name": row["name"],
        "builder": row["builder"],
        "bhk": row["bhk"],
        "price": row["price"],
        "location": row["location"],
        "tag": row["tag"]
    }