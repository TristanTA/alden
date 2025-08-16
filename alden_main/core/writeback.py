# Applies planner write-backs to the calendar:
#  - Reschedules: update event start time to new_start
#  - Focus blocks: create events for gap blocks (optional)
#  - Weekly anchors: create anchor focus events across the week

from datetime import datetime
from typing import List, Dict

from utils.config import CONFIG
from alden_calendar.calendar import update_event, add_event


def _today_iso_at(hhmm: str) -> str:
    today = datetime.now().date().isoformat()
    return f"{today}T{hhmm}"


def _iso_at_date(date_iso: str, hhmm: str) -> str:
    return f"{date_iso}T{hhmm}"


def apply_reschedules(reschedules: List[Dict]) -> List[str]:
    """Write back rescheduled start times. Returns human messages."""
    msgs = []
    for r in reschedules:
        eid = r.get("id") or r.get("title")
        new_iso = r.get("new_start")
        if not eid or not new_iso:
            continue
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


def materialize_weekly_anchors(week_outline: Dict) -> List[str]:
    """
    Create anchor events across the provided week outline.
    Expects week_outline from planning.weekly_planner.plan_week (with anchor_suggestions).
    """
    msgs: List[str] = []
    if not CONFIG.get("weekly_anchors", {}).get("enabled", True):
        return msgs

    cat = CONFIG["weekly_anchors"].get("default_category", "focus")

    for day in week_outline.get("days", []):
        date_iso = day.get("date")
        anchors = day.get("anchor_suggestions", [])
        for a in anchors:
            title = a.get("title", "Focus Anchor")
            start = a.get("start")
            end = a.get("end")
            priority = a.get("priority", "normal")
            if not start or not end or not date_iso:
                continue

            # Compute duration
            try:
                sh = datetime.strptime(start, "%H:%M")
                eh = datetime.strptime(end, "%H:%M")
                duration_min = int((eh - sh).total_seconds() // 60)
                if duration_min <= 0:
                    continue
            except Exception:
                duration_min = CONFIG["weekly_anchors"].get("default_duration_min", 60)

            iso = _iso_at_date(date_iso, start)
            ev = add_event(
                title=title,
                time_str=iso,
                category=cat,
                priority=priority,
                duration_min=duration_min
            )
            msgs.append(f"Created anchor: {title} on {date_iso} @ {start} ({duration_min}m)")
    return msgs