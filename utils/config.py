# Config flags and runtime settings

CONFIG = {
    "debug_mode": True,
    "use_api": True,
    "calendar_enabled": True,

    # Nudge controls (used by nudger + notifications)
    "nudges": {
        "prep_high_minutes": 10,
        "prep_normal_minutes": 5,
        "wrap_minutes": 2,
        "gap_mid_check_min_duration": 60
    },

    # Notifications: convert plan into timestamped nudges (no delivery here)
    "notifications": {
        "enabled": True,
        "types": {
            "prep": True,
            "mid_gap_check": True,
            "wrap": True,
            "day_wrap": True
        },
        "workday": {"start": "08:00", "end": "20:00"}
    },

    # Delivery (read-only outbox for now)
    "delivery": {
        "enabled": True,
        "console_echo": True,                  # print to stdout too
        "outbox_path": "outbox/nudges.jsonl"   # appended JSON Lines file
    },

    # Budgeting (wire to LLM calls later)
    "budget": {
        "enabled": True,
        "weekly_limit_usd": 8.0
    },

    # --- Write-back controls ---
    "write_back": {
        "enabled": False,
        "materialize_focus_blocks": False,
        "focus_block": {
            "title": "Focus Block",
            "category": "focus",
            "priority": "normal",
            "duration_min_default": 60
        }
    },

    # Weekly anchor suggestions (for week planning + write-back)
    "weekly_anchors": {
        "enabled": True,
        # Python weekday(): Mon=0 … Sun=6
        "by_weekday": {
            "0": [{"title": "Deep Work", "start": "09:00", "end": "11:00", "priority": "high"}],
            "1": [{"title": "Deep Work", "start": "09:00", "end": "11:00", "priority": "high"}],
            "2": [{"title": "Deep Work", "start": "09:00", "end": "11:00", "priority": "high"}],
            "3": [{"title": "Deep Work", "start": "09:00", "end": "11:00", "priority": "high"}],
            "4": [{"title": "Deep Work", "start": "09:00", "end": "11:00", "priority": "high"}]
        },
        "default_category": "focus",
        "default_duration_min": 60
    }
}