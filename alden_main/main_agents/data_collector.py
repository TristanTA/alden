import sqlite3
import datetime
import json
from typing import Dict, Any

DB_PATH = "alden.db"

# -----------------------
# DB INIT
# -----------------------
def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS location_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            platform TEXT,
            event TEXT,
            latitude REAL,
            longitude REAL,
            address TEXT,
            ts REAL,              -- store as epoch seconds
            stored_at TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            ts REAL,
            platform TEXT,
            event TEXT,
            app TEXT,
            title TEXT,
            stored_at TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE,
            name TEXT,
            email TEXT,
            created_at REAL,
            stored_at TEXT
        )""")
    print("✅ DB initialized")

def _utc_now_iso() -> str:
    return datetime.datetime.utcnow().isoformat()

# -----------------------
# VALIDATORS
# -----------------------
def _validate_location(payload: Dict[str, Any]) -> None:
    if "device_id" not in payload or "ts" not in payload or "coords" not in payload:
        raise ValueError("LOCATION requires device_id, ts, and coords")
    if not isinstance(payload["coords"], dict):
        raise ValueError("coords must be a dict")
    if "lat" not in payload["coords"] or "lon" not in payload["coords"]:
        raise ValueError("coords must have lat and lon")

def _validate_usage(payload: Dict[str, Any]) -> None:
    if "device_id" not in payload or "ts" not in payload or "event" not in payload:
        raise ValueError("USAGE requires device_id, ts, and event")

def _validate_user(payload: Dict[str, Any]) -> None:
    if "user_id" not in payload:
        raise ValueError("USER requires user_id")

VALIDATORS = {
    "LOCATION": _validate_location,
    "USAGE": _validate_usage,
    "USER": _validate_user,
}

# -----------------------
# STORE FUNCTIONS
# -----------------------
def _store_location(con: sqlite3.Connection, payload: Dict[str, Any]) -> int:
    ts = datetime.datetime.fromisoformat(payload["ts"]).timestamp()
    coords = payload["coords"]
    cur = con.execute(
        """INSERT INTO location_events
           (device_id, platform, event, latitude, longitude, address, ts, stored_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            payload["device_id"],
            payload.get("platform"),
            payload.get("event"),
            float(coords["lat"]),
            float(coords["lon"]),
            payload.get("address"),
            ts,
            _utc_now_iso(),
        ),
    )
    return cur.lastrowid

def _store_usage(con: sqlite3.Connection, payload: Dict[str, Any]) -> int:
    ts = datetime.datetime.fromisoformat(payload["ts"]).timestamp()
    cur = con.execute(
        """INSERT INTO usage_events
           (device_id, ts, platform, event, app, title, stored_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            payload["device_id"],
            ts,
            payload.get("platform"),
            payload["event"],
            payload.get("app"),
            payload.get("title"),
            _utc_now_iso(),
        ),
    )
    return cur.lastrowid

def _store_user(con: sqlite3.Connection, payload: Dict[str, Any]) -> int:
    ts = datetime.datetime.fromisoformat(payload["created_at"]).timestamp() \
        if isinstance(payload["created_at"], str) else payload["created_at"].timestamp()
    cur = con.execute(
        """INSERT OR REPLACE INTO users
           (user_id, name, email, created_at, stored_at)
           VALUES (?, ?, ?, ?, ?)""",
        (
            payload["user_id"],
            payload.get("name"),
            payload.get("email"),
            ts,
            _utc_now_iso(),
        ),
    )
    return cur.lastrowid

STORES = {
    "LOCATION": _store_location,
    "USAGE": _store_usage,
    "USER": _store_user,
}

# -----------------------
# PUBLIC API
# -----------------------
def validate(category: str, payload: Dict[str, Any]) -> None:
    if category not in VALIDATORS:
        raise ValueError(f"unknown_category:{category}")
    VALIDATORS[category](payload)

def store_data(category: str, payload: Dict[str, Any]) -> int:
    if category not in STORES:
        raise ValueError(f"unknown_category:{category}")
    with sqlite3.connect(DB_PATH) as con:
        return STORES[category](con, payload)
