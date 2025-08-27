import datetime
import json
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

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
