# Local-only calendar system (with duration support)

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

CALENDAR_FILE = Path("alden_calendar/calendar_db.json")


def load_calendar() -> List[Dict]:
    if not CALENDAR_FILE.exists():
        save_calendar([])
    with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_calendar(events: List[Dict]) -> None:
    with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


def add_event(
    title: str,
    time_str: str,
    category: str = "general",
    priority: str = "normal",
    duration_min: int = 60,
) -> Dict:
    """Create a new event. time_str must be ISO-like (YYYY-MM-DDTHH:MM)."""
    events = load_calendar()
    ev = {
        "id": str(uuid.uuid4()),
        "title": title,
        "time": time_str,             # ISO 8601 string
        "category": category,
        "priority": priority,         # low | normal | high
        "duration_min": int(duration_min),
        "status": "scheduled",        # scheduled | done | canceled
        "created": datetime.now().isoformat()
    }
    events.append(ev)
    save_calendar(events)
    return ev


def list_events() -> List[Dict]:
    return load_calendar()


def get_today_events() -> List[Dict]:
    now = datetime.now().date().isoformat()
    return [e for e in load_calendar() if e.get("time", "").startswith(now)]


def get_events_between(start_iso: str, end_iso: str) -> List[Dict]:
    events = load_calendar()
    try:
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
    except Exception:
        return []
    out = []
    for e in events:
        try:
            t = datetime.fromisoformat(e.get("time", ""))
        except Exception:
            continue
        if start <= t <= end:
            out.append(e)
    return out


def _match_id_or_title(ev: Dict, id_or_title: str) -> bool:
    return ev.get("id") == id_or_title or ev.get("title") == id_or_title


def delete_event(id_or_title: str) -> bool:
    events = load_calendar()
    new_events = [e for e in events if not _match_id_or_title(e, id_or_title)]
    changed = len(new_events) != len(events)
    if changed:
        save_calendar(new_events)
    return changed


def update_event(id_or_title: str, **fields) -> Optional[Dict]:
    """Update fields (title, time, category, priority, status, duration_min)."""
    events = load_calendar()
    updated = None
    for e in events:
        if _match_id_or_title(e, id_or_title):
            if "duration_min" in fields and fields["duration_min"] is not None:
                try:
                    fields["duration_min"] = int(fields["duration_min"])
                except Exception:
                    pass
            e.update({k: v for k, v in fields.items() if v is not None})
            updated = e
            break
    if updated:
        save_calendar(events)
    return updated


def mark_done(id_or_title: str) -> Optional[Dict]:
    return update_event(id_or_title, status="done")