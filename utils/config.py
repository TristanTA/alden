# Config flags and runtime settings

CONFIG = {
    "debug_mode": True,
    "use_api": True,
    "calendar_enabled": True,

    # Nudge controls
    "nudges": {
        "prep_high_minutes": 10,
        "prep_normal_minutes": 5,
        "wrap_minutes": 2,
        "gap_mid_check_min_duration": 60
    },

    # Budgeting (wire later)
    "budget": {
        "enabled": True,
        "weekly_limit_usd": 8.0
    },

    # --- Write-back controls ---
    "write_back": {
        # If True, Alden will write changes to the calendar:
        # - apply reschedules determined by the planner
        # - optionally create focus block events for gaps
        "enabled": False,

        # Only materialize focus gaps if this is True:
        "materialize_focus_blocks": False,

        # Title and defaults for focus blocks Alden creates:
        "focus_block": {
            "title": "Focus Block",
            "category": "focus",
            "priority": "normal",  # low | normal | high
            "duration_min_default": 60  # used if we need a fallback
        }
    }
}