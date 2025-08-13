# Build a timestamped nudge schedule from a daily plan.
# This does NOT send notifications; it only returns a schedule that a future
# delivery adapter can consume.

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List
from utils.config import CONFIG


def _hhmm_to_dt_for_day(hhmm: str, ref: datetime | None = None) -> datetime | None:
    try:
        h, m = hhmm.split(":")
        base = ref or datetime.now()
        return base.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
    except Exception:
        return None


def build_nudge_schedule(plan: Dict, ref: datetime | None = None) -> List[Dict]:
    """
    Returns a list of nudges with precise timestamps.
    Each nudge dict: { "at": ISO, "type": "prep|mid|wrap|day_wrap", "message": str }
    """
    if not CONFIG.get("notifications", {}).get("enabled", True):
        return []

    types = CONFIG["notifications"]["types"]
    ncfg = CONFIG["nudges"]

    out: List[Dict] = []
    ref = ref or datetime.now()

    for blk in plan.get("blocks", []):
        start = _hhmm_to_dt_for_day(blk.get("start", ""), ref)
        end = _hhmm_to_dt_for_day(blk.get("end", ""), ref)
        if not start or not end:
            continue

        title = blk.get("title", "Untitled")
        pr = blk.get("priority", "normal")
        src = blk.get("source", "gap")

        # PREP
        if types.get("prep", True) and src == "event":
            delta = ncfg["prep_high_minutes"] if pr == "high" else ncfg["prep_normal_minutes"]
            at = start - timedelta(minutes=delta)
            out.append({
                "at": at.isoformat(timespec="minutes"),
                "type": "prep",
                "message": f"Prep for **{title}** at {at.strftime('%H:%M')} ({pr})."
            })

        # MID GAP CHECK (only for long gaps)
        if types.get("mid_gap_check", True) and src == "gap":
            dur_min = int((end - start).total_seconds() // 60)
            if dur_min >= CONFIG["nudges"]["gap_mid_check_min_duration"]:
                mid = start + (end - start) / 2
                out.append({
                    "at": mid.isoformat(timespec="minutes"),
                    "type": "mid",
                    "message": f"Mid-block check-in {mid.strftime('%H:%M')}: still on **{title}**?"
                })

        # WRAP
        if types.get("wrap", True):
            wrap_at = end - timedelta(minutes=CONFIG["nudges"]["wrap_minutes"])
            out.append({
                "at": wrap_at.isoformat(timespec="minutes"),
                "type": "wrap",
                "message": f"Wrap **{title}** at {wrap_at.strftime('%H:%M')}: capture notes/next step."
            })

    # DAY WRAP (after last block)
    if types.get("day_wrap", True) and plan.get("blocks"):
        last_end = plan["blocks"][-1]["end"]
        last_dt = _hhmm_to_dt_for_day(last_end, ref)
        if last_dt:
            out.append({
                "at": last_dt.isoformat(timespec="minutes"),
                "type": "day_wrap",
                "message": f"Day wrap at {last_dt.strftime('%H:%M')}: 2‑min reflection + tomorrow first task."
            })

    out.sort(key=lambda n: n["at"])
    return out