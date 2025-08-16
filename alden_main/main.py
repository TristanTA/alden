# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import json
import os

app = FastAPI()

CALENDAR_FILE = "alden_main/alden_calendar/calendar_db.json"

# --- Models ---
class Event(BaseModel):
    title: str
    time: str  # ISO format e.g. "2025-08-20T15:00:00Z"

class PlanResponse(BaseModel):
    plan: list[str]

class NextEventResponse(BaseModel):
    next_event: str | None
    time: str | None

class StatusResponse(BaseModel):
    status: str
    event_id: str | None = None

# --- Helpers ---
def load_calendar():
    if not os.path.exists(CALENDAR_FILE):
        return []
    with open(CALENDAR_FILE, "r") as f:
        return json.load(f)

def save_calendar(events):
    with open(CALENDAR_FILE, "w") as f:
        json.dump(events, f, indent=2)

# --- Endpoints ---
@app.get("/api/plan/today", response_model=PlanResponse)
def get_plan_today():
    events = load_calendar()
    today = datetime.now().date().isoformat()
    todays_events = [
        f"{e['title']} at {e['time']}"
        for e in events
        if e['time'].startswith(today)
    ]
    return {"plan": todays_events}

@app.get("/api/plan/next", response_model=NextEventResponse)
def get_next_event():
    events = load_calendar()
    now = datetime.utcnow().isoformat()
    upcoming = sorted(
        [e for e in events if e['time'] > now],
        key=lambda e: e['time']
    )
    if upcoming:
        return {"next_event": upcoming[0]['title'], "time": upcoming[0]['time']}
    return {"next_event": None, "time": None}

@app.post("/api/calendar/add", response_model=StatusResponse)
def add_calendar_event(event: Event):
    events = load_calendar()
    event_id = f"evt_{len(events)+1}"
    events.append({"id": event_id, "title": event.title, "time": event.time})
    save_calendar(events)
    return {"status": "ok", "event_id": event_id}
