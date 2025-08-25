from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import datetime, json, os

app = FastAPI(title="Alden API v2")

# -------------------------
# MODELS
# -------------------------
class LocationEvent(BaseModel):
    device_id: str
    name: str = Field(..., description="Friendly place name, e.g., 'Home' or 'BYUI Library'")
    latitude: float
    longitude: float
    ts: float = Field(..., description="Epoch timestamp when recorded")

class UsageEvent(BaseModel):
    device_id: str
    ts: float = Field(..., description="Epoch timestamp")
    app: Optional[str] = None        # package/exe name
    event: str                       # "foreground" | "idle" | "unlock" | "lock" | etc.
    duration_s: Optional[float] = None
    extra: Optional[dict] = None

# -------------------------
# FILE STORAGE (TEMP DB STUB)
# -------------------------
LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)

def append_log(filename: str, entry: dict):
    """Append line-delimited JSON for now (easy swap to DB later)."""
    path = os.path.join(LOG_DIR, filename)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

# -------------------------
# ENDPOINTS
# -------------------------

@app.get("/ping")
def ping():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}

@app.post("/shortcut-test")
async def shortcut_test(request: Request):
    data = await request.json()
    entry = {"timestamp": datetime.datetime.utcnow().isoformat(), "data": data}
    append_log("shortcut_logs.jsonl", entry)
    return {"received": data, "status": "logged"}

@app.post("/location")
async def post_location(ev: LocationEvent):
    entry = {"timestamp": datetime.datetime.utcnow().isoformat(), **ev.model_dump()}
    append_log("location.jsonl", entry)
    return {"ok": True, "stored": ev.dict()}

@app.post("/usage")
async def post_usage(ev: UsageEvent):
    entry = {"timestamp": datetime.datetime.utcnow().isoformat(), **ev.model_dump()}
    append_log("usage.jsonl", entry)
    return {"ok": True, "stored": ev.dict()}
