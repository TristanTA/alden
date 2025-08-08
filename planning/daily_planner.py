# Daily planner with durations and overlap handling + write-back metadata.
#
# Inputs: list of events with keys:
#   id, title, time (ISO), category, priority (low|normal|high), duration_min, status
#
# Behavior:
#   - Parses event start times
#   - Uses duration_min (default 60 if missing/invalid)
#   - Sorts by start time, then priority (high > normal > low)
#   - Resolves overlaps by keeping higher-priority in place and shifting lower-priority
#     to start after the higher-priority event ends.
#   - Emits nudges describing any reschedules.
#   - Also returns metadata so the brain can WRITE BACK changes:
#       reschedules: [{"id","title","old_start","new_start","duration_min"}]
#       focus_blocks: [{"start","end"}]   # HH:MM strings (based on ref day)
#
# Output:
#   {
#     "blocks": [{start, end, title, priority, source, event_id?}, ...],
#     "nudges": [str, ...],
#     "reschedules": [ ... ],
#     "focus_blocks": [ ... ]
#   }

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional


WORK_START = (8, 0)   # 08:00
WORK_END   = (20, 0)  # 20:00
MIN_GAP_BLOCK_MIN = 30


def _priority_weight(p: str) -> int:
    order = {"high": 0, "normal": 1, "low": 2}
    return order.get((p or "normal").lower(), 1)


def _parse_time(iso_str: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(iso_str)
    except Exception:
        return None


def _get_duration(e: Dict) -> int:
    try:
        d = int(e.get("duration_min", 60))
        return max(5, min(d, 12 * 60))  # clamp: 5 min to 12 hours
    except Exception:
        return 60


def _fmt_hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _work_bounds(day: datetime) -> Tuple[datetime, datetime]:
    start = day.replace(hour=WORK_START[0], minute=WORK_START[1], second=0, microsecond=0)
    end   = day.replace(hour=WORK_END[0],   minute=WORK_END[1],   second=0, microsecond=0)
    return start, end


def plan_day(events: List[Dict], ref_date: Optional[datetime] = None) -> Dict:
    """
    Plan a single day. By default uses 'today'; pass ref_date to plan other days.
    ref_date's date() is used for filtering and work bounds.
    """
    now = ref_date or datetime.now()
    day_start, day_end = _work_bounds(now)

    # Filter to ref_date's events, parse times, attach metadata
    todays = []
    for e in events:
        t = _parse_time(e.get("time", ""))
        if not t or t.date() != now.date():
            continue
        e = dict(e)  # shallow copy
        e["_start"] = t
        e["_dur"] = _get_duration(e)
        e["_end"] = t + timedelta(minutes=e["_dur"])
        e["_pwt"] = _priority_weight(e.get("priority"))
        todays.append(e)

    # Sort by (start time, priority weight)
    todays.sort(key=lambda e: (e["_start"], e["_pwt"]))

    blocks: List[Dict] = []
    nudges: List[str] = []
    reschedules: List[Dict] = []

    # De-conflict overlaps:
    scheduled: List[Dict] = []
    for e in todays:
        if not scheduled:
            scheduled.append(e)
            continue

        last = scheduled[-1]
        if e["_start"] >= last["_end"]:
            scheduled.append(e)
            continue

        # Overlap detected. Decide which event stays.
        if e["_pwt"] < last["_pwt"]:
            # New event higher priority → shift last forward
            old_start = last["_start"]
            moved = dict(last)
            moved["_start"] = max(e["_end"], moved["_start"])
            moved["_end"] = moved["_start"] + timedelta(minutes=moved["_dur"])
            scheduled[-1] = e
            scheduled.append(moved)
            reschedules.append({
                "id": last.get("id"),
                "title": last.get("title", "(untitled)"),
                "old_start": old_start.isoformat(timespec="minutes"),
                "new_start": moved["_start"].isoformat(timespec="minutes"),
                "duration_min": moved["_dur"]
            })
            nudges.append(
                f"Rescheduled **{last.get('title','(untitled)')}** to {_fmt_hhmm(moved['_start'])} "
                f"due to conflict with high-priority **{e.get('title','(untitled)')}**."
            )
        else:
            # Existing last higher or equal priority → shift e after last
            old_start = e["_start"]
            moved = dict(e)
            moved["_start"] = last["_end"]
            moved["_end"] = moved["_start"] + timedelta(minutes=moved["_dur"])
            scheduled.append(moved)
            reschedules.append({
                "id": e.get("id"),
                "title": e.get("title", "(untitled)"),
                "old_start": old_start.isoformat(timespec="minutes"),
                "new_start": moved["_start"].isoformat(timespec="minutes"),
                "duration_min": moved["_dur"]
            })
            nudges.append(
                f"Rescheduled **{e.get('title','(untitled)')}** to {_fmt_hhmm(moved['_start'])} "
                f"due to conflict with **{last.get('title','(untitled)')}**."
            )

    # Build plan blocks; also collect focus gaps for optional write-back
    cursor = day_start
    focus_blocks: List[Dict] = []

    def _add_gap(until: datetime, default_priority="normal"):
        nonlocal blocks, cursor, focus_blocks
        if until <= cursor:
            return
        gap_len = int((until - cursor).total_seconds() // 60)
        if gap_len >= MIN_GAP_BLOCK_MIN:
            blocks.append({
                "start": _fmt_hhmm(cursor),
                "end": _fmt_hhmm(until),
                "title": "Open Focus Block",
                "priority": default_priority,
                "source": "gap"
            })
            focus_blocks.append({"start": _fmt_hhmm(cursor), "end": _fmt_hhmm(until)})
        cursor = until

    for e in scheduled:
        evt_start = max(e["_start"], day_start)
        evt_end = min(e["_end"], day_end)

        _add_gap(evt_start)

        # Add event block
        if evt_end > evt_start:
            blocks.append({
                "start": _fmt_hhmm(evt_start),
                "end": _fmt_hhmm(evt_end),
                "title": e.get("title", "Untitled"),
                "priority": (e.get("priority") or "normal"),
                "source": "event",
                "event_id": e.get("id")
            })
            cursor = evt_end

    # Post-end gap
    if cursor < day_end:
        gap_len = int((day_end - cursor).total_seconds() // 60)
        if gap_len >= MIN_GAP_BLOCK_MIN:
            blocks.append({
                "start": _fmt_hhmm(cursor),
                "end": _fmt_hhmm(day_end),
                "title": "Open Focus Block",
                "priority": "low",
                "source": "gap"
            })
            focus_blocks.append({"start": _fmt_hhmm(cursor), "end": _fmt_hhmm(day_end)})

    # No events at all: default structure (no write-back metadata for these)
    if not scheduled:
        blocks = [
            {"start": "09:00", "end": "11:00", "title": "Deep Work", "priority": "high", "source": "gap"},
            {"start": "11:00", "end": "12:00", "title": "Admin / Messages", "priority": "normal", "source": "gap"},
            {"start": "13:00", "end": "15:00", "title": "Project Block", "priority": "normal", "source": "gap"},
            {"start": "15:30", "end": "17:00", "title": "Light Tasks", "priority": "low", "source": "gap"},
        ]
        nudges.append("No events this day—proposed a focus-first schedule.")
        focus_blocks = []
        reschedules = []

    return {
        "blocks": blocks,
        "nudges": nudges,
        "reschedules": reschedules,
        "focus_blocks": focus_blocks
    }