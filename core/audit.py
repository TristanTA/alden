# Plan audit logger (records what actually happened) + simple readers.

from __future__ import annotations
from pathlib import Path
import json
from typing import Dict, Optional
from datetime import datetime

LOG_PATH = Path("data/plan_log.jsonl")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def log_block_outcome(
    date_iso: str,
    title: str,
    planned_start_hhmm: str,
    planned_end_hhmm: str,
    outcome: str,                    # "done" | "partial" | "skipped"
    actual_start_iso: Optional[str] = None,
    actual_end_iso: Optional[str] = None,
    notes: str = ""
) -> None:
    """Append a block outcome to the audit log."""
    _ensure_parent(LOG_PATH)
    rec = {
        "date": date_iso,                        # YYYY-MM-DD (day of the block)
        "title": title,
        "planned_start": planned_start_hhmm,
        "planned_end": planned_end_hhmm,
        "outcome": outcome,
        "actual_start": actual_start_iso,
        "actual_end": actual_end_iso,
        "notes": notes,
        "ts": datetime.now().isoformat(timespec="seconds")
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def iter_log():
    if not LOG_PATH.exists():
        return
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue