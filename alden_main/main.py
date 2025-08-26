import datetime
import sqlite3
import json
import os
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

DB_PATH = "alden.db"

# -----------------------
# MODELS
# -----------------------
class LocationEvent(BaseModel):
    device_id: str
    name: str = Field(..., description="Friendly place name")
    latitude: float
    longitude: float
    ts: float  # epoch seconds

class UsageEvent(BaseModel):
    device_id: str
    ts: float
    app: Optional[str] = None
    event: str  # "foreground" | "idle" | "unlock" | "lock"
    duration_s: Optional[float] = None
    extra: Optional[dict] = None

class User(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    created_at: float = Field(default_factory=lambda: datetime.datetime.utcnow().timestamp())

# -----------------------
# DB SETUP
# -----------------------
def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS location_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            name TEXT,
            latitude REAL,
            longitude REAL,
            ts REAL,
            stored_at TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            ts REAL,
            app TEXT,
            event TEXT,
            duration_s REAL,
            extra_json TEXT,
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

init_db()

# -----------------------
# HELPERS
# -----------------------
def _utc_now_iso() -> str:
    return datetime.datetime.utcnow().isoformat()

# -----------------------
# APP
# -----------------------
app = FastAPI(title="Alden API Clean")

@app.get("/ping")
def ping():
    return {"status": "ok", "time": _utc_now_iso()}

@app.post("/shortcut-test")
async def shortcut_test(request: Request):
    data = await request.json()
    entry = {"timestamp": _utc_now_iso(), "data": data}
    with open("shortcut_logs.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    return {"received": data, "status": "logged"}

@app.post("/location")
async def post_location(ev: LocationEvent):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""INSERT INTO location_events
            (device_id, name, latitude, longitude, ts, stored_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (ev.device_id, ev.name, ev.latitude, ev.longitude, ev.ts, _utc_now_iso()))
    return {"ok": True, "stored": ev.dict()}

@app.post("/usage")
async def post_usage(ev: UsageEvent):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""INSERT INTO usage_events
            (device_id, ts, app, event, duration_s, extra_json, stored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ev.device_id, ev.ts, ev.app, ev.event,
             ev.duration_s, json.dumps(ev.extra) if ev.extra else None, _utc_now_iso()))
    return {"ok": True, "stored": ev.dict()}

@app.post("/user")
async def post_user(user: User):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""INSERT OR REPLACE INTO users
            (user_id, name, email, created_at, stored_at)
            VALUES (?, ?, ?, ?, ?)""",
            (user.user_id, user.name, user.email, user.created_at, _utc_now_iso()))
    return {"ok": True, "stored": user.dict()}
