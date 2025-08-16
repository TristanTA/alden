# Core logic handler

from utils.debug import debug_log
from utils.config import CONFIG
from core.state import AppState
from planning.daily_planner import plan_day
from core.nudger import build_nudges_for_plan

# Adjust if you renamed your calendar package differently
from alden_calendar.calendar import get_today_events

# Write-back helpers
from core.writeback import apply_reschedules, materialize_focus_blocks


def run():
    print('[Alden] Booting up logic core...')
    state = AppState()
    debug_log('State initialized')

    # One debug tick for now
    debug_log('Main loop tick')

    if CONFIG.get('calendar_enabled', True):
        events = get_today_events()
        debug_log(f'Loaded {len(events)} event(s) for today')
    else:
        events = []
        debug_log('Calendar disabled by config')

    plan = plan_day(events)
    # Attach nudges computed from the plan
    plan['nudges'].extend(build_nudges_for_plan(plan))

    # --- Optional write-back phase ---
    wb_cfg = CONFIG.get("write_back", {})
    if wb_cfg.get("enabled"):
        debug_log("Write-back enabled: applying reschedules.")
        res_msgs = apply_reschedules(plan.get("reschedules", []))
        for m in res_msgs:
            debug_log(m)

        if wb_cfg.get("materialize_focus_blocks"):
            debug_log("Materializing focus blocks as events.")
            fb_msgs = materialize_focus_blocks(plan.get("focus_blocks", []))
            for m in fb_msgs:
                debug_log(m)
    else:
        debug_log("Write-back disabled; no calendar modifications will be made.")

    state.context['today_plan'] = plan

    # Debug output of plan
    print('\n=== Alden: Proposed Daily Plan ===')
    for block in plan['blocks']:
        print(f"- {block['start']}–{block['end']}: {block['title']} "
              f"[{block['priority']}] ({block['source']})")

    if plan['nudges']:
        print("\nNudges:")
        for n in plan['nudges']:
            print(f"- {n}")

    # Show planned write-back actions (summary)
    if wb_cfg.get("enabled"):
        print("\n[Write-back] Reschedules to apply:", len(plan.get("reschedules", [])))
        if wb_cfg.get("materialize_focus_blocks"):
            print("[Write-back] Focus blocks to create:", len(plan.get("focus_blocks", [])))

    debug_log('Tick complete')