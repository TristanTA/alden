import datetime
import json
import sqlite3
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from alden_main.main_agents.data_collector import validate, store_data, init_db

# -----------------------
# MODELS
# -----------------------
class LocationEvent(BaseModel):
    device_id: str
    ts: float  # epoch seconds
    platform: Optional[str] = None  # "ios" | "macos" | "windows" | "android"
    event: Optional[str] = None     # "location"
    coords: dict = Field(..., description="{'lat': float, 'lon': float}")
    address: Optional[str] = None

class UsageEvent(BaseModel):
    device_id: str
    ts: float
    platform: Optional[str] = None  # "ios" | "macos" | "windows" | "android"
    event: str                      # "foreground" | "closed"
    app: Optional[str] = None
    title: Optional[str] = None

class User(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    created_at: float = Field(default_factory=lambda: datetime.datetime.utcnow().timestamp())

# -----------------------
# APP
# -----------------------
app = FastAPI(title="Alden API")
init_db()

@app.get("/ping")
def ping():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}

@app.post("/shortcut-test")
async def shortcut_test(request: Request):
    data = await request.json()
    entry = {"timestamp": datetime.datetime.utcnow().isoformat(), "data": data}
    with open("shortcut_logs.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    return {"received": data, "status": "logged"}

@app.post("/location")
async def post_location(ev: LocationEvent):
    payload = ev.dict(by_alias=True)
    validate("LOCATION", payload)
    row_id = store_data("LOCATION", payload)
    return {"ok": True, "id": row_id, "stored": payload}

@app.post("/usage")
async def post_usage(ev: UsageEvent):
    payload = ev.dict(by_alias=True)
    validate("USAGE", payload)
    row_id = store_data("USAGE", payload)
    return {"ok": True, "id": row_id, "stored": payload}

@app.post("/user")
async def post_user(user: User):
    payload = user.dict()
    validate("USER", payload)
    row_id = store_data("USER", payload)
    return {"ok": True, "id": row_id, "stored": payload}
