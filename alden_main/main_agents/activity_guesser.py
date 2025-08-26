# backend/agents/activity_guesser.py
from __future__ import annotations
from typing import Dict, Any
import json, os
from datetime import datetime, timezone
from models.gpt5nano import run_gpt5nano

def guess(feature_bundle: Dict[str, Any], *, api_mode: bool = False, debug: bool = False) -> Dict[str, Any]:
    system_prompt = """You are an assistant that infers a user's most likely activity
from summarized mobile telemetry. Return JSON with keys: label, confidence, rationale, evidence.
The label is a short string (e.g., "WORK", "LEISURE", "TRAVEL"). Confidence is a float [0.0, 1.0].
Rationale is a human-readable explanation of the guess. Evidence is a JSON object with keys seen.
Example output:
{
    "label": "WORK",
    "confidence": 0.85,
    "rationale": "User has recent calendar events and screen usage indicating work-related activity.",
    "evidence": {
        "keys_seen": ["calendar", "screen_usage"]
    },
    "version": "gpt5nano_v0"
}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(feature_bundle, ensure_ascii=False)},
    ]

    if not api_mode:
        result = {
            "label": "UNKNOWN",
            "confidence": 0.5,
            "rationale": "api_mode=False (dry-run)",
            "evidence": {"keys_seen": list(feature_bundle.keys())},
            "version": "gpt5nano_v0_dryrun",
        }
        if debug:
            print(f"[GUESS.DRYRUN] {result}")
        log_activity(result, debug=debug)
        return {"status": "ok", "guess": result}
    if api_mode:
        raw_output = run_gpt5nano(messages, debug=debug)
        result = json.loads(raw_output)  # however you currently parse GPT output
        log_activity(result, debug=debug)
        return result
    
LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # go up from main_agents to backend
    "stores",
    "activity_log.jsonl"
)

def log_activity(activity_data: dict, debug: bool = False) -> None:
    """
    Append an activity guess to the log file with a UTC timestamp.
    Uses JSON Lines format so it can be read incrementally.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "activity": activity_data
    }
    if debug:
        print(f"[LOG_ACTIVITY] {entry}")
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    if debug:
        print(f"[LOG_ACTIVITY] Activity logged to {LOG_PATH}")