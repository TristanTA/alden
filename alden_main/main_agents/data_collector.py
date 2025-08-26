# data_collector.py
"""
Minimal, single-DB Data Collector.

What this does
--------------
- Uses ONE SQLite database (stores.db) with multiple tables.
- Every record carries a shared `flow_id` (groups events that belong to the same end-to-end run).
- Each table has its own `local_id` (INTEGER PRIMARY KEY) so you can distinguish multiple rows
  for the same flow (e.g., many calendar events in one flow).
- Every row has `ts_utc` so you can measure latency later.

Public API
----------
- init_db(debug=False): create tables/indexes if missing.
- validate(category, payload): light checks for required fields & timestamp formats.
- send_data(category, payload, flow_id=None, debug=False): validate + store into the right table(s).
  If flow_id is None, we auto-generate one.

Notes
-----
- Keep payloads small and structured. We only store the necessary fields right now.
- All times are ISO 8601. If you add 'Z', we normalize to +00:00.
"""

from __future__ import annotations
from typing import Dict, Any, Literal, Callable, List, Tuple, Optional
import sqlite3
from datetime import datetime, timezone
import os
import json
import uuid

Category = Literal["GPS", "CALENDAR", "SCREEN_USAGE", "USER"]

# ----------------------- helpers -----------------------

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stores"))
DB_PATH = os.path.join(_BASE, "stores.db")

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _iso_to_dt(s: str) -> datetime:
    """Parse ISO 8601 strings; supports trailing 'Z'. Raises ValueError if invalid."""
    if not isinstance(s, str):
        raise ValueError("timestamp must be a string")
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)

def _ensure_dir() -> None:
    os.makedirs(_BASE, exist_ok=True)

def _gen_flow_id() -> str:
    """Stable enough for dev; replace with your own if needed."""
    return f"flow_{uuid.uuid4().hex[:12]}"

# ----------------------- init (one DB) -----------------------

def init_db(debug: bool = False) -> None:
    """
    Create all tables and indexes in a single SQLite database.
    Minimal columns only; every table has:
      - local_id (INTEGER PRIMARY KEY)
      - flow_id (TEXT, indexed)
      - ts_utc (TEXT, ISO 8601 insert time)
    """
    _ensure_dir()
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()

        # Flows registry: helpful for quick day queries and existence checks
        cur.execute("""
        CREATE TABLE IF NOT EXISTS flows (
            flow_id    TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS gps (
            local_id INTEGER PRIMARY KEY,
            flow_id  TEXT NOT NULL,
            ts_utc   TEXT NOT NULL,
            lat      REAL NOT NULL,
            lon      REAL NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS calendar_events (
            local_id   INTEGER PRIMARY KEY,
            flow_id    TEXT NOT NULL,
            ts_utc     TEXT NOT NULL,
            event_id   TEXT,         -- optional external id
            title      TEXT NOT NULL,
            start_utc  TEXT NOT NULL,
            end_utc    TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS screen_usage_sessions (
            local_id         INTEGER PRIMARY KEY,
            flow_id          TEXT NOT NULL,
            ts_utc           TEXT NOT NULL,
            app_name         TEXT NOT NULL,
            package_name     TEXT NOT NULL,
            start_utc        TEXT NOT NULL,
            end_utc          TEXT,         -- may be empty if unknown
            duration_seconds INTEGER       -- may be null if unknown
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_events (
            local_id INTEGER PRIMARY KEY,
            flow_id  TEXT NOT NULL,
            ts_utc   TEXT NOT NULL,
            data_json TEXT NOT NULL        -- opaque debug/audit blob
        )
        """)

        # Indexes for fast reconstruction by flow and time windows
        cur.execute("CREATE INDEX IF NOT EXISTS ix_gps_flow ON gps(flow_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_cal_flow ON calendar_events(flow_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_screen_flow ON screen_usage_sessions(flow_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_user_flow ON user_events(flow_id)")

        cur.execute("CREATE INDEX IF NOT EXISTS ix_gps_ts ON gps(ts_utc)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_cal_ts ON calendar_events(ts_utc)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_screen_ts ON screen_usage_sessions(ts_utc)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_user_ts ON user_events(ts_utc)")

    if debug:
        print(f"[INIT] Stores initialized at {DB_PATH}")

from typing import Dict, Any, Callable
from datetime import datetime

def _validate_location(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("LOCATION payload must be an object")
    for k in ("device_id", "name", "latitude", "longitude", "ts"):
        if k not in payload:
            raise ValueError(f"LOCATION missing '{k}'")
    float(payload["latitude"])
    float(payload["longitude"])
    float(payload["ts"])

def _validate_usage(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("USAGE payload must be an object")
    for k in ("device_id", "ts", "event"):
        if k not in payload:
            raise ValueError(f"USAGE missing '{k}'")
    float(payload["ts"])
    if payload.get("duration_s") is not None:
        float(payload["duration_s"])
    if "extra" in payload and payload["extra"] is not None and not isinstance(payload["extra"], dict):
        raise ValueError("USAGE.extra must be a dict")

def _validate_user(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("USER payload must be an object")
    if "user_id" not in payload:
        raise ValueError("USER missing 'user_id'")
    if "email" in payload and payload["email"] not in (None, ""):
        if "@" not in payload["email"]:
            raise ValueError("USER.email must be valid")

# registry
VALIDATORS: dict[str, Callable[[Dict[str, Any]], None]] = {
    "LOCATION": _validate_location,
    "USAGE": _validate_usage,
    "USER": _validate_user,
}

# ----------------------- store (single DB) -----------------------

def _ensure_flow(con: sqlite3.Connection, flow_id: str) -> None:
    con.execute(
        "INSERT OR IGNORE INTO flows(flow_id, created_at) VALUES (?, ?)",
        (flow_id, _utc_now_iso()),
    )

def _store_gps(con: sqlite3.Connection, flow_id: str, payload: Dict[str, Any]) -> int:
    ts = _utc_now_iso()
    if "coords" in payload:
        lat_str, lon_str = payload["coords"].split(",", 1)
        lat, lon = float(lat_str.strip()), float(lon_str.strip())
    else:
        lat, lon = float(payload["lat"]), float(payload["lon"])
    cur = con.execute(
        "INSERT INTO gps(flow_id, ts_utc, lat, lon) VALUES(?, ?, ?, ?)",
        (flow_id, ts, lat, lon),
    )
    return cur.lastrowid

def _store_calendar(con: sqlite3.Connection, flow_id: str, payload: Dict[str, Any]) -> int:
    ts = _utc_now_iso()
    events = payload.get("events", [])
    rows = []
    for ev in events:
        rows.append((
            flow_id, ts,
            str(ev.get("event_id", "")),
            str(ev.get("title", "")),
            str(ev.get("start_time", "")),
            str(ev.get("end_time", "")),
        ))
    if not rows:
        return 0
    con.executemany(
        """INSERT INTO calendar_events(flow_id, ts_utc, event_id, title, start_utc, end_utc)
           VALUES(?, ?, ?, ?, ?, ?)""",
        rows
    )
    return len(rows)

def _store_screen_usage(con: sqlite3.Connection, flow_id: str, payload: Dict[str, Any]) -> int:
    ts = _utc_now_iso()
    sessions = payload.get("sessions", [])
    rows = []
    for s in sessions:
        start = str(s.get("start_time", ""))
        end = s.get("end_time")
        dur = s.get("duration_seconds")
        # compute duration if not provided but end exists
        if dur is None and end not in (None, ""):
            try:
                dt_start = _iso_to_dt(start)
                dt_end = _iso_to_dt(str(end))
                dur = max(0, int((dt_end - dt_start).total_seconds()))
            except Exception:
                dur = None
        if end is None:
            end = ""  # keep empty string if unknown
        rows.append((
            flow_id, ts,
            str(s.get("app_name", "")),
            str(s.get("package_name", "")),
            start,
            str(end),
            int(dur) if dur is not None else None
        ))
    if not rows:
        return 0
    con.executemany(
        """INSERT INTO screen_usage_sessions(flow_id, ts_utc, app_name, package_name, start_utc, end_utc, duration_seconds)
           VALUES(?, ?, ?, ?, ?, ?, ?)""",
        rows
    )
    return len(rows)

def _store_user(con: sqlite3.Connection, flow_id: str, payload: Dict[str, Any]) -> int:
    ts = _utc_now_iso()
    blob = json.dumps(payload, ensure_ascii=False)
    cur = con.execute(
        "INSERT INTO user_events(flow_id, ts_utc, data_json) VALUES(?, ?, ?)",
        (flow_id, ts, blob),
    )
    return cur.lastrowid

STORES: dict[Category, Callable[[sqlite3.Connection, str, Dict[str, Any]], int]] = {
    "GPS": _store_gps,
    "CALENDAR": _store_calendar,
    "SCREEN_USAGE": _store_screen_usage,
    "USER": _store_user,
}

# ----------------------- public API -----------------------

def validate(category: Category, payload: Dict[str, Any]) -> None:
    """Light validation per category."""
    if category not in VALIDATORS:
        raise ValueError(f"unknown_category:{category}")
    VALIDATORS[category](payload)

def send_data(category: Category, payload: Dict[str, Any], *, flow_id: Optional[str] = None, debug: bool = False) -> Dict[str, Any]:
    """
    Validate and store into a single DB.
    - category: "GPS" | "CALENDAR" | "SCREEN_USAGE" | "USER"
    - payload: category-shaped dict
    - flow_id: optional; generated if None (returned to caller)
    Returns: {"status":"ok","category":..., "flow_id":..., "rows": n}
    """
    if debug:
        print(f"[DEBUG] category={category} received; validating...")

    validate(category, payload)

    init_db(debug=False)
    if flow_id is None:
        flow_id = _gen_flow_id()

    rows = 0
    with sqlite3.connect(DB_PATH) as con:
        _ensure_flow(con, flow_id)
        rows = STORES[category](con, flow_id, payload)

    if debug:
        print(f"[DEBUG] {category} stored rows={rows} flow_id={flow_id}")

    return {"status": "ok", "category": category, "flow_id": flow_id, "rows": rows}