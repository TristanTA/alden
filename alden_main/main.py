import datetime
import json
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from alden_main.main_agents.data_collector import validate, store_data, init_db
from alden_main.main_agents.routes_calendar import router as caldav_router

# -----------------------
# MODELS
# -----------------------
class Coordinates(BaseModel):
    lat: float
    lon: float

class LocationEvent(BaseModel):
    device_id: str
    ts: datetime.datetime  # ISO8601 string → parsed automatically
    platform: Optional[str] = None
    event: Optional[str] = None
    coords: Coordinates
    address: Optional[str] = None

class UsageEvent(BaseModel):
    device_id: str
    ts: datetime.datetime  # ISO8601
    platform: Optional[str] = None
    event: str
    app: Optional[str] = None
    title: Optional[str] = None

class User(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.utcnow())

# -----------------------
# APP
# -----------------------
app = FastAPI(title="Alden API")
init_db()
app.include_router(caldav_router)

@app.get("/ping")
def ping():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}

@app.post("/shortcut-test")
async def shortcut_test(request: Request):
    data = await request.json()
    entry = {"timestamp": datetime.datetime.utcnow().isoformat(), "data": data}
    with open("shortcut_logs.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    print("📥 SHORTCUT TEST:", entry)
    return {"received": data, "status": "logged"}

def _unwrap_json(data: dict):
    """Handle Shortcuts wrapping everything in a 'json' key"""
    if isinstance(data, dict) and "json" in data and isinstance(data["json"], str):
        try:
            return json.loads(data["json"])
        except Exception as e:
            print("❌ Failed to parse inner JSON:", e)
            return data
    return data

# -----------------------
# ENDPOINTS
# -----------------------
@app.post("/location")
async def post_location(request: Request):
    data = await request.json()
    data = _unwrap_json(data)
    print("📥 RAW LOCATION DATA:", data)

    try:
        ev = LocationEvent(**data)
        payload = ev.dict()
        row_id = store_data("LOCATION", payload)
        print("✅ STORED LOCATION:", payload)
        return {"ok": True, "id": row_id, "stored": payload}
    except Exception as e:
        print("❌ ERROR storing LOCATION:", e)
        return {"ok": False, "error": str(e), "raw": data}

@app.post("/usage")
async def post_usage(request: Request):
    data = await request.json()
    data = _unwrap_json(data)
    print("📥 RAW USAGE DATA:", data)

    try:
        ev = UsageEvent(**data)
        payload = ev.dict()
        row_id = store_data("USAGE", payload)
        print("✅ STORED USAGE:", payload)
        return {"ok": True, "id": row_id, "stored": payload}
    except Exception as e:
        print("❌ ERROR storing USAGE:", e)
        return {"ok": False, "error": str(e), "raw": data}

@app.post("/user")
async def post_user(request: Request):
    data = await request.json()
    data = _unwrap_json(data)
    print("📥 RAW USER DATA:", data)

    try:
        ev = User(**data)
        payload = ev.dict()
        row_id = store_data("USER", payload)
        print("✅ STORED USER:", payload)
        return {"ok": True, "id": row_id, "stored": payload}
    except Exception as e:
        print("❌ ERROR storing USER:", e)
        return {"ok": False, "error": str(e), "raw": data}

import os, asyncio
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alden_main.models.models_calendar import Base
from alden_main.main_agents.caldav_client import AldenCalDAV
from alden_main.main_agents.calendar_sync import poll_loop

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./alden.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(engine)

caldav = AldenCalDAV()

app = FastAPI()

@app.on_event("startup")
def startup():
    app.state.caldav = AldenCalDAV()
    # Optional: try a light touch to log readiness, but don’t crash on failure
    try:
        _ = app.state.caldav.get_calendars()
        print("✅ CalDAV reachable")
    except Exception as e:
        print(f"⚠️ CalDAV not reachable yet: {e}")

app.include_router(caldav_router, prefix="/calendar")

@app.on_event("startup")
async def _startup():
    asyncio.create_task(poll_loop(caldav, SessionLocal, int(os.getenv("POLL_SECONDS","60"))))
    
from alden_main.main_agents.routes_calendar import mount_calendar_routes
mount_calendar_routes(app, SessionLocal, caldav)

