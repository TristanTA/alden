# Token budget tracker (dumb local counter for now)
# Integrate with OpenAI calls later; for now, call record() wherever you'd spend tokens.

from pathlib import Path
import json
from datetime import datetime

BUDGET_FILE = Path("budget_usage.json")

DEFAULT = {
    "period": "weekly",  # "daily" | "weekly" | "monthly"
    "limit_usd": 8.0,
    "history": []        # entries: {ts, tokens_in, tokens_out, usd_estimate, note}
}

PRICE_PER_1K_INPUT = 0.005  # placeholder; update with real pricing when you wire API
PRICE_PER_1K_OUTPUT = 0.015


def _load():
    if not BUDGET_FILE.exists():
        _save(DEFAULT)
    with BUDGET_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    with BUDGET_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def estimate_cost(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in / 1000.0) * PRICE_PER_1K_INPUT + (tokens_out / 1000.0) * PRICE_PER_1K_OUTPUT


def record(tokens_in: int, tokens_out: int, note: str = "") -> float:
    data = _load()
    usd = estimate_cost(tokens_in, tokens_out)
    data["history"].append({
        "ts": datetime.now().isoformat(),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "usd_estimate": round(usd, 4),
        "note": note,
    })
    _save(data)
    return usd


def total_spend(period: str | None = None) -> float:
    # TODO: date-filter by period; for now, return grand total
    data = _load()
    return round(sum(h["usd_estimate"] for h in data["history"]), 4)


def set_limit(limit_usd: float, period: str = "weekly"):
    data = _load()
    data["limit_usd"] = float(limit_usd)
    data["period"] = period
    _save(data)