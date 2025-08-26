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
    ts: float  # epoch seconds
    platform: Optional[str] = None
    event: Optional[str] = None
    coords: Coordinates
    address: Optional[str] = None

class UsageEvent(BaseModel):
    device_id: str
    ts: float
    platform: Optional[str] = None
    event: str
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
async def post_location(request: Request):
    data = await request.json()
    # If it's wrapped in "text", try to parse inner JSON
    if "text" in data and isinstance(data["text"], str):
        try:
            inner = json.loads(data["text"])
            print("📥 Unwrapped inner JSON:", inner)
            data = inner
        except Exception as e:
            print("❌ Failed to parse inner text JSON:", e)
    
    print("📥 FINAL LOCATION DATA:", data)
    for k, v in data.items():
        print(f"   {k}: {v!r} (type={type(v).__name__})")
        if isinstance(v, dict):
            for kk, vv in v.items():
                print(f"      {kk}: {vv!r} (type={type(vv).__name__})")

    ev = LocationEvent(**data)  # now should validate correctly
    payload = ev.dict(by_alias=True)
    row_id = store_data("LOCATION", payload)
    return {"ok": True, "id": row_id, "stored": payload}


    # let Pydantic validate
    ev = LocationEvent(**data)
    payload = ev.dict(by_alias=True)
    validate("LOCATION", payload)
    row_id = store_data("LOCATION", payload)
    return {"ok": True, "id": row_id, "stored": payload}

@app.post("/usage")
async def post_usage(request: Request):
    data = await request.json()
    print("📥 RAW USAGE DATA:", data)
    for k, v in data.items():
        print(f"   {k}: {v!r} (type={type(v).__name__})")

    ev = UsageEvent(**data)
    payload = ev.dict(by_alias=True)
    validate("USAGE", payload)
    row_id = store_data("USAGE", payload)
    return {"ok": True, "id": row_id, "stored": payload}

@app.post("/user")
async def post_user(request: Request):
    data = await request.json()
    print("📥 RAW USER DATA:", data)
    for k, v in data.items():
        print(f"   {k}: {v!r} (type={type(v).__name__})")

    ev = User(**data)
    payload = ev.dict()
    validate("USER", payload)
    row_id = store_data("USER", payload)
    return {"ok": True, "id": row_id, "stored": payload}
