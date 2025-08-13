# Nudger: decides WHEN to prompt based on plan blocks
#
# Input plan format:
# {
#   "blocks": [{start, end, title, priority, source}, ...],  # HH:MM
#   "nudges": [str, ...]
# }
# Output: list of additional nudge strings (human-readable for now)

from datetime import datetime, timedelta


def _to_dt_today(hhmm: str) -> datetime | None:
    try:
        h, m = hhmm.split(":")
        now = datetime.now()
        return now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
    except Exception:
        return None


def build_nudges_for_plan(plan: dict) -> list[str]:
    extra = []
    for blk in plan.get("blocks", []):
        start = _to_dt_today(blk.get("start", ""))
        end = _to_dt_today(blk.get("end", ""))
        title = blk.get("title", "Untitled")
        pr = blk.get("priority", "normal")
        src = blk.get("source", "gap")

        if not start or not end:
            continue

        # Pre-start prep: 10 min for high, 5 min for normal
        if src == "event":
            delta = 10 if pr == "high" else 5
            prep = (start - timedelta(minutes=delta)).strftime("%H:%M")
            extra.append(f"Prep for **{title}** at {prep} ({pr}).")

        # Mid-block poke for gap focus blocks ≥ 60 min
        if src == "gap":
            dur_min = int((end - start).total_seconds() // 60)
            if dur_min >= 60:
                mid = (start + (end - start) / 2).strftime("%H:%M")
                extra.append(f"Mid-block check-in at {mid}: staying on **{title}**?")

        # End-of-block wrap
        wrap = (end - timedelta(minutes=2)).strftime("%H:%M")
        extra.append(f"Wrap **{title}** at {wrap}: capture notes or next step.")

    # Day-end reflection
    if plan.get("blocks"):
        last_end = plan["blocks"][-1]["end"]
        extra.append(f"Day wrap at {last_end}: 2-min reflection + tomorrow first task.")

    return extra