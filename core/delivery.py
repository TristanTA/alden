# Delivery adapter (read-only for now): writes timestamped nudges to an outbox (JSONL)
# and optionally echoes to console.

from __future__ import annotations
from pathlib import Path
import json
from typing import List, Dict
from datetime import datetime
from utils.config import CONFIG


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_nudges_jsonl(nudges: List[Dict], out_path: str | Path = None) -> int:
    """Append nudges to JSONL outbox. Returns count written."""
    if out_path is None:
        out_path = CONFIG["delivery"]["outbox_path"]
    p = Path(out_path)
    ensure_parent(p)

    count = 0
    with p.open("a", encoding="utf-8") as f:
        for n in nudges:
            # Normalize record
            rec = {
                "at": n.get("at"),                         # ISO minute timestamp
                "type": n.get("type"),                     # prep|mid|wrap|day_wrap
                "message": n.get("message"),
                "created": datetime.now().isoformat(timespec="seconds"),
                "source": "alden"
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    return count


def echo_to_console(nudges: List[Dict]) -> None:
    for n in nudges:
        print(f"{n['at']}  [{n['type']}]  {n['message']}")


def deliver_nudges(nudges: List[Dict]) -> int:
    """Main entry: echo + write to outbox if enabled. Returns count written."""
    if CONFIG["delivery"].get("console_echo", True):
        echo_to_console(nudges)
    if CONFIG["delivery"].get("enabled", True):
        return write_nudges_jsonl(nudges)
    return 0