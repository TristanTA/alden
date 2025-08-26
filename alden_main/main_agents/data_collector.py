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
            ts REAL,
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
    if "device_id" not in payload or "ts" not in payload or "coordinates" not in payload:
        raise ValueError("LOCATION requires device_id, ts, and coordinates")
    coords = payload["coordinates"]
    if not isinstance(coords, dict) or "lat" not in coords or "lon" not in coords:
        raise ValueError("LOCATION.coordinates must include 'lat' and 'lon'")
    float(coords["lat"]); float(coords["lon"]); float(payload["ts"])

def _validate_usage(payload: Dict[str, Any]) -> None:
    if "device_id" not in payload or "ts" not in payload or "event" not in payload:
        raise ValueError("USAGE requires device_id, ts, and event")
    float(payload["ts"])

def _validate_user(payload: Dict[str, Any]) -> None:
    if "user_id" not in payload:
        raise ValueError("USER requires user_id")
    if "email" in payload and payload["email"] not in (None, ""):
        if "@" not in payload["email"]:
            raise ValueError("USER.email must be valid")

VALIDATORS = {
    "LOCATION": _validate_location,
    "USAGE": _validate_usage,
    "USER": _validate_user,
}

# -----------------------
# STORE FUNCTIONS
# -----------------------
def _store_location(con: sqlite3.Connection, payload: Dict[str, Any]) -> int:
    coords = payload["coordinates"]
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
            float(payload["ts"]),
            _utc_now_iso(),
        ),
    )
    return cur.lastrowid

def _store_usage(con: sqlite3.Connection, payload: Dict[str, Any]) -> int:
    cur = con.execute(
        """INSERT INTO usage_events
           (device_id, ts, platform, event, app, title, stored_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            payload["device_id"],
            float(payload["ts"]),
            payload.get("platform"),
            payload["event"],
            payload.get("app"),
            payload.get("title"),
            _utc_now_iso(),
        ),
    )
    return cur.lastrowid

def _store_user(con: sqlite3.Connection, payload: Dict[str, Any]) -> int:
    cur = con.execute(
        """INSERT OR REPLACE INTO users
           (user_id, name, email, created_at, stored_at)
           VALUES (?, ?, ?, ?, ?)""",
        (
            payload["user_id"],
            payload.get("name"),
            payload.get("email"),
            float(payload.get("created_at", datetime.datetime.utcnow().timestamp())),
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
