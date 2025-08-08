# Applies planner write-backs to the calendar:
#  - Reschedules: update event start time to new_start
#  - Focus blocks: create new events for gap blocks (optional)
#
# NOTE: This intentionally uses "today" for HH:MM-only times.

from datetime import datetime
from typing import List, Dict

from utils.config import CONFIG
from alden_calendar.calendar import update_event, add_event


def _today_iso_at(hhmm: str) -> str:
    today = datetime.now().date().isoformat()
    return f"{today}T{hhmm}"


def apply_reschedules(reschedules: List[Dict]) -> List[str]:
    """Write back rescheduled start times. Returns human messages."""
    msgs = []
    for r in reschedules:
        eid = r.get("id") or r.get("title")
        new_iso = r.get("new_start")
        if not eid or not new_iso:
            continue
        # Ensure we store full ISO with minutes
        ok = update_event(eid, time=new_iso)
        if ok:
            msgs.append(f"Updated {ok.get('title')} → {ok.get('time')}")
    return msgs


def materialize_focus_blocks(focus_blocks: List[Dict]) -> List[str]:
    """Create calendar events for each gap block (using config defaults)."""
    msgs = []
    fb_cfg = CONFIG["write_back"]["focus_block"]
    title = fb_cfg["title"]
    category = fb_cfg["category"]
    priority = fb_cfg["priority"]

    for fb in focus_blocks:
        start_hhmm = fb.get("start")
        end_hhmm = fb.get("end")
        if not start_hhmm or not end_hhmm:
            continue

        # Compute duration
        try:
            sh = datetime.strptime(start_hhmm, "%H:%M")
            eh = datetime.strptime(end_hhmm, "%H:%M")
            duration_min = int((eh - sh).total_seconds() // 60)
            if duration_min <= 0:
                continue
        except Exception:
            duration_min = fb_cfg.get("duration_min_default", 60)

        iso = _today_iso_at(start_hhmm)
        ev = add_event(
            title=title,
            time_str=iso,
            category=category,
            priority=priority,
            duration_min=duration_min
        )
        msgs.append(f"Created focus block: {ev['title']} @ {ev['time']} ({duration_min}m)")
    return msgs