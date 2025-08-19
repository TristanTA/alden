# Calendar storage and helpers (JSON file)
from __future__ import annotations
import json
import uuid
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Optional

# Store DB next to this file
_DB_PATH = Path(__file__).parent / "calendar_db.json"

def _read_db() -> List[Dict]:
    if not _DB_PATH.exists():
        _write_db([])
    with _DB_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def _write_db(rows: List[Dict]) -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _DB_PATH.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def list_events() -> List[Dict]:
    return _read_db()

def create_event(title: str, start_iso: str, end_iso: str,
                 location: Optional[str] = None, notes: Optional[str] = None,
                 category: Optional[str] = None, priority: Optional[str] = None,
                 duration_min: Optional[int] = None, status: Optional[str] = None) -> Dict:
    ev = {
        "id": str(uuid.uuid4()),
        "title": title,
        "start_iso": start_iso,
        "end_iso": end_iso,
        "location": location,
        "notes": notes,
        "category": category,
        "priority": priority,
        "duration_min": duration_min,
        "status": status or "scheduled",
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"
    }
    rows = _read_db()
    rows.append(ev)
    _write_db(rows)
    return ev

def update_event(event_id: str, **fields) -> Optional[Dict]:
    rows = _read_db()
    updated = None
    for r in rows:
        if r.get("id") == event_id:
            for k, v in fields.items():
                if v is not None:
                    r[k] = v
            updated = r
            break
    if updated:
        _write_db(rows)
    return updated

def delete_event(event_id: str) -> bool:
    rows = _read_db()
    new_rows = [r for r in rows if r.get("id") != event_id]
    if len(new_rows) == len(rows):
        return False
    _write_db(new_rows)
    return True

def events_on_date(d: date) -> List[Dict]:
    rows = _read_db()
    out = []
    for r in rows:
        try:
            start = datetime.fromisoformat(r["start_iso"].replace("Z",""))
        except Exception:
            continue
        if start.date() == d:
            out.append(r)
    out.sort(key=lambda r: r.get("start_iso",""))
    return out
