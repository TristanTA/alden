# Local-only calendar system

import json
from datetime import datetime
from pathlib import Path

CALENDAR_FILE = Path("calendar/calendar_db.json")

def load_calendar():
    if not CALENDAR_FILE.exists():
        save_calendar([])
    with open(CALENDAR_FILE, "r") as f:
        return json.load(f)

def save_calendar(events):
    with open(CALENDAR_FILE, "w") as f:
        json.dump(events, f, indent=2)

def add_event(title, time_str, category="general", priority="normal"):
    events = load_calendar()
    events.append({
        "title": title,
        "time": time_str,
        "category": category,
        "priority": priority,
        "created": datetime.now().isoformat()
    })
    save_calendar(events)

def get_today_events():
    events = load_calendar()
    today = datetime.now().date().isoformat()
    return [e for e in events if e["time"].startswith(today)]

def delete_event(title):
    events = load_calendar()
    events = [e for e in events if e["title"] != title]
    save_calendar(events)
