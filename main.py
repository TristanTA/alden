from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from alden_main.alden_calendar import calendar as cal
import json, os

app = FastAPI()

class UsageEvent(BaseModel):
    device_id: str
    ts: float                    # epoch seconds
    platform: str                # "android" | "windows" | "linux" | "mac"
    event: str                   # "foreground" | "idle" | "unlock" | "lock" | etc.
    app: Optional[str] = None    # package/exe name
    title: Optional[str] = None  # window/app title
    duration_s: Optional[float] = None
    idle_s: Optional[float] = None
    extra: Optional[dict] = None

# very light auth
ALDEN_INGEST_TOKEN = os.getenv("ALDEN_INGEST_TOKEN", "dev-token")
LOG_DIR = "./usage_logs"
os.makedirs(LOG_DIR, exist_ok=True)

@app.post("/ingest/usage")
async def ingest_usage(ev: UsageEvent, x_alden_token: str = Header(None)):
    if x_alden_token != ALDEN_INGEST_TOKEN:
        return {"ok": False, "error": "bad token"}
    # append line-delimited JSON (easy to parse later)
    path = os.path.join(LOG_DIR, f"{ev.device_id}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev.model_dump()) + "\n")
    return {"ok": True}

app = FastAPI(title="Alden API")

class CreateEventRequest(BaseModel):
    title: str
    start_iso: str = Field(..., description="ISO8601 start, e.g. 2025-08-20T10:00:00")
    end_iso: str = Field(..., description="ISO8601 end")
    location: Optional[str] = None
    notes: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = Field(default=None, pattern="^(low|normal|high)?$")
    duration_min: Optional[int] = None
    status: Optional[str] = None

class UpdateEventRequest(BaseModel):
    title: Optional[str] = None
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = Field(default=None, pattern="^(low|normal|high)?$")
    duration_min: Optional[int] = None
    status: Optional[str] = None

class MessageResponse(BaseModel):
    message: str

class EventOut(BaseModel):
    id: str
    title: str
    start_iso: str
    end_iso: str
    location: Optional[str] = None
    notes: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    duration_min: Optional[int] = None
    status: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok"}

# Add event
@app.post("/api/events", response_model=MessageResponse)
def add_event(body: CreateEventRequest):
    ev = cal.create_event(**body.dict())
    return MessageResponse(message=f"{ev['title']} saved")

# Edit event
@app.put("/api/events/{event_id}", response_model=EventOut)
def edit_event(event_id: str, body: UpdateEventRequest):
    ev = cal.update_event(event_id, **{k:v for k,v in body.dict().items() if v is not None})
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventOut(**ev)

# Delete event
@app.delete("/api/events/{event_id}", response_model=MessageResponse)
def delete_event(event_id: str):
    ok = cal.delete_event(event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")
    return MessageResponse(message="deleted")

# Get daily schedule
@app.get("/api/schedule/daily", response_model=List[EventOut])
def daily(date_str: Optional[str] = None):
    if date_str:
        try:
            d = datetime.fromisoformat(date_str).date()
        except Exception:
            # allow YYYY-MM-DD
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                raise HTTPException(status_code=400, detail="Bad date")
    else:
        d = datetime.now().date()
    rows = cal.events_on_date(d)
    return [EventOut(**r) for r in rows]

# Simple daily planning: generate blocks, detect gaps (very basic)
class PlanResponse(BaseModel):
    blocks: List[dict]
    nudges: List[str]

@app.post("/api/plan/daily", response_model=PlanResponse)
def plan_daily(date_str: Optional[str] = None):
    if date_str:
        try:
            d = datetime.fromisoformat(date_str).date()
        except Exception:
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                raise HTTPException(status_code=400, detail="Bad date")
    else:
        d = datetime.now().date()
    events = cal.events_on_date(d)
    # Build blocks with times
    parsed = []
    for e in events:
        try:
            start = datetime.fromisoformat(e["start_iso"].replace("Z",""))
            end = datetime.fromisoformat(e["end_iso"].replace("Z",""))
        except Exception:
            continue
        parsed.append({"start": start, "end": end, "title": e.get("title","(untitled)"), "priority": e.get("priority","normal")})
    parsed.sort(key=lambda x: x["start"])
    # Create gaps -> propose focus work
    blocks = []
    nudges = []
    for b in parsed:
        blocks.append({
            "start": b["start"].strftime("%H:%M"),
            "end": b["end"].strftime("%H:%M"),
            "title": b["title"],
            "priority": b["priority"],
            "source": "event"
        })
    # Suggest one focus block if there is no event between 9-11
    has_morning = any((blk["start"] <= "09:00" < blk["end"]) or ("09:00" <= blk["start"] < "11:00") for blk in blocks)
    if not has_morning:
        blocks.insert(0, {"start":"09:00","end":"11:00","title":"Deep Work","priority":"high","source":"gap"})
        nudges.append("Suggested a 09:00–11:00 Deep Work block.")
    return PlanResponse(blocks=blocks, nudges=nudges)
