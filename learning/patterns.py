# Learns simple preferred time windows from audit log and saves preferences.

from __future__ import annotations
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import json
from typing import Dict

from core.audit import iter_log

PREF_PATH = Path("learning/preferences.json")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def hhmm_to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def minutes_to_hhmm(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def learn_preferences() -> Dict:
    """
    Aggregate by rough priority inferred from title keywords.
    Uses 'done' and 'partial' outcomes only.

    Output:
    {
      "by_priority": {
         "high": {"preferred_start": "09:15"},
         "normal": {"preferred_start": "13:30"},
         "low": {"preferred_start": "16:00"}
      }
    }
    """
    buckets = defaultdict(list)

    for rec in iter_log() or []:
        outcome = (rec.get("outcome") or "").lower()
        if outcome not in ("done", "partial"):
            continue
        title = (rec.get("title") or "").lower()
        start = rec.get("planned_start")
        if not start:
            continue

        if "deep work" in title or "focus" in title:
            pr = "high"
        elif "errand" in title or "light" in title:
            pr = "low"
        else:
            pr = "normal"

        buckets[pr].append(hhmm_to_minutes(start))

    prefs = {"by_priority": {}}
    for pr, minutes_list in buckets.items():
        if not minutes_list:
            continue
        avg = sum(minutes_list) // len(minutes_list)
        prefs["by_priority"][pr] = {"preferred_start": minutes_to_hhmm(avg)}

    _ensure_parent(PREF_PATH)
    with PREF_PATH.open("w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2, ensure_ascii=False)

    return prefs