# Weekly planner skeleton.
#
# Builds a 7-day outline (configurable) by calling daily_planner.plan_day
# for each date, then summarizes priorities and capacity.
#
# Output format:
# {
#   "days": [
#       {
#         "date": "2025-08-08",
#         "plan": { blocks, nudges, reschedules, focus_blocks },
#         "summary": {
#            "events": N,
#            "high": N, "normal": N, "low": N,
#            "scheduled_minutes": M,
#            "focus_minutes": M,
#            "free_minutes": M
#         }
#       },
#       ...
#   ],
#   "totals": { ... }   # weekly aggregates
# }

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from planning.daily_planner import plan_day
from alden_calendar.calendar import list_events


def _to_date(d: Optional[str]) -> datetime:
    if d:
        return datetime.fromisoformat(d)
    return datetime.now()


def _minutes(blocks: List[Dict], source_filter: Optional[str] = None) -> int:
    total = 0
    for b in blocks:
        if source_filter and b.get("source") != source_filter:
            continue
        try:
            sh, sm = b["start"].split(":")
            eh, em = b["end"].split(":")
            start = int(sh) * 60 + int(sm)
            end = int(eh) * 60 + int(em)
            total += max(0, end - start)
        except Exception:
            continue
    return total


def _priority_counts(blocks: List[Dict]) -> Dict[str, int]:
    cnt = {"high": 0, "normal": 0, "low": 0}
    for b in blocks:
        p = (b.get("priority") or "normal").lower()
        if p in cnt:
            cnt[p] += 1
    return cnt


def plan_week(start_date_iso: Optional=str, days: int = 7) -> Dict:
    """Produce a week outline starting at start_date_iso (YYYY-MM-DD) or today."""
    start_dt = _to_date(start_date_iso)
    all_events = list_events()  # We'll filter by date per-day

    days_out = []
    totals = {
        "events": 0,
        "high": 0, "normal": 0, "low": 0,
        "scheduled_minutes": 0,
        "focus_minutes": 0,
        "free_minutes": 0
    }

    for i in range(days):
        ref = start_dt + timedelta(days=i)
        ref_date_str = ref.date().isoformat()

        # Filter events for this day
        day_events = [e for e in all_events if (e.get("time","").startswith(ref_date_str))]

        plan = plan_day(day_events, ref_date=ref)

        pr_counts = _priority_counts([b for b in plan["blocks"] if b.get("source") == "event"])
        scheduled_min = _minutes(plan["blocks"], source_filter="event")
        focus_min = _minutes(plan["blocks"], source_filter="gap")

        # 12h day capacity by default (match daily planner bounds)
        total_day_capacity = 12 * 60
        free_min = max(0, total_day_capacity - (scheduled_min + focus_min))

        summary = {
            "events": pr_counts["high"] + pr_counts["normal"] + pr_counts["low"],
            "high": pr_counts["high"], "normal": pr_counts["normal"], "low": pr_counts["low"],
            "scheduled_minutes": scheduled_min,
            "focus_minutes": focus_min,
            "free_minutes": free_min
        }

        days_out.append({
            "date": ref_date_str,
            "plan": plan,
            "summary": summary
        })

        # Aggregate totals
        totals["events"] += summary["events"]
        totals["high"] += summary["high"]
        totals["normal"] += summary["normal"]
        totals["low"] += summary["low"]
        totals["scheduled_minutes"] += scheduled_min
        totals["focus_minutes"] += focus_min
        totals["free_minutes"] += free_min

    return {"days": days_out, "totals": totals}