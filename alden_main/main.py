import datetime
import json
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from typing import Optional

from alden_main.main_agents.data_collector import validate, store_data, init_db

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

def _unwrap_json(data: dict):
    """Handle Shortcuts wrapping everything in a 'json' key"""
    if isinstance(data, dict) and "json" in data and isinstance(data["json"], str):
        try:
            return json.loads(data["json"])
        except Exception as e:
            print("❌ Failed to parse inner JSON:", e)
            return data
    return data

@app.post("/location")
async def post_location(request: Request):
    data = await request.json()
    data = _unwrap_json(data)
    ev = LocationEvent(**data)
    payload = ev.dict()
    row_id = store_data("LOCATION", payload)
    return {"ok": True, "id": row_id, "stored": payload}

@app.post("/usage")
async def post_usage(request: Request):
    data = await request.json()
    data = _unwrap_json(data)
    ev = UsageEvent(**data)
    payload = ev.dict()
    row_id = store_data("USAGE", payload)
    return {"ok": True, "id": row_id, "stored": payload}

@app.post("/user")
async def post_user(request: Request):
    data = await request.json()
    data = _unwrap_json(data)
    ev = User(**data)
    payload = ev.dict()
    row_id = store_data("USER", payload)
    return {"ok": True, "id": row_id, "stored": payload}
