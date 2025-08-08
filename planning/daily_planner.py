# Daily planner (lightweight / heuristic)
#
# Input: list of events (dicts) with keys:
#   id, title, time (ISO), category, priority, status
# Output: plan dict:
#   {
#     "blocks": [{start, end, title, priority, source}],   # source: "event"|"gap"
#     "nudges": [str, ...]
#   }

from datetime import datetime, timedelta


def _priority_weight(p):
    order = {"high": 0, "normal": 1, "low": 2}
    return order.get(p or "normal", 1)


def _parse_time(iso_str):
    # Accepts "YYYY-MM-DDTHH:MM" or full ISO
    try:
        return datetime.fromisoformat(iso_str)
    except Exception:
        # fallback: ignore parse errors by returning None
        return None


def _event_duration_minutes(ev):
    # Simple default: 60 minutes if not encoded in title (we can expand later)
    return 60


def plan_day(events):
    now = datetime.now()
    start_of_day = now.replace(hour=8, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=20, minute=0, second=0, microsecond=0)

    # Filter to today + parse times
    todays = []
    for e in events:
        t = _parse_time(e.get("time", ""))
        if not t:
            continue
        if t.date() == now.date():
            e["_dt"] = t
            todays.append(e)

    # Sort by (time, priority)
    todays.sort(key=lambda e: (e["_dt"], _priority_weight(e.get("priority"))))

    # Build blocks from events (assume 60min default)
    blocks = []
    cursor = start_of_day
    nudges = []

    for e in todays:
        evt_start = e["_dt"]
        evt_end = evt_start + timedelta(minutes=_event_duration_minutes(e))

        # If there is a gap before this event, insert a "gap" focus block
        if evt_start > cursor:
            gap_len = (evt_start - cursor).seconds // 60
            if gap_len >= 30:  # only schedule gaps >= 30min
                blocks.append({
                    "start": cursor.strftime("%H:%M"),
                    "end": evt_start.strftime("%H:%M"),
                    "title": "Open Focus Block",
                    "priority": "normal",
                    "source": "gap"
                })

        # Add event block
        status = e.get("status", "scheduled")
        title = e.get("title", "Untitled")
        prio = e.get("priority", "normal")
        blocks.append({
            "start": evt_start.strftime("%H:%M"),
            "end": evt_end.strftime("%H:%M"),
            "title": title,
            "priority": prio,
            "source": "event"
        })

        # Nudge: if high priority, suggest preparing 10 min in advance
        if prio == "high":
            prep_time = (evt_start - timedelta(minutes=10)).strftime("%H:%M")
            nudges.append(f"Prep for **{title}** at {prep_time} (high priority).")

        # If the event is marked done already, note it
        if status == "done":
            nudges.append(f"✅ Already completed: {title}")

        # Move cursor
        if evt_end > cursor:
            cursor = evt_end

    # Fill end-of-day gap
    if cursor < end_of_day:
        gap_len = (end_of_day - cursor).seconds // 60
        if gap_len >= 30:
            blocks.append({
                "start": cursor.strftime("%H:%M"),
                "end": end_of_day.strftime("%H:%M"),
                "title": "Open Focus Block",
                "priority": "low",
                "source": "gap"
            })

    # If no events, propose a simple structure
    if not todays:
        blocks = [
            {"start": "09:00", "end": "11:00", "title": "Deep Work", "priority": "high", "source": "gap"},
            {"start": "11:00", "end": "12:00", "title": "Admin / Messages", "priority": "normal", "source": "gap"},
            {"start": "13:00", "end": "15:00", "title": "Project Block", "priority": "normal", "source": "gap"},
            {"start": "15:30", "end": "17:00", "title": "Light Tasks", "priority": "low", "source": "gap"},
        ]
        nudges.append("No events today—proposed a focus-first schedule.")

    return {"blocks": blocks, "nudges": nudges}
