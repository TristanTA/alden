# Core logic handler

from utils.debug import debug_log
from utils.config import CONFIG
from core.state import AppState
from planning.daily_planner import plan_day
from core.nudger import build_nudges_for_plan

# If you renamed your calendar package, update this import accordingly:
from alden_calendar.calendar import get_today_events  # <-- rename if needed


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
    # Attach nudges computed from the plan (prep reminders, soft pokes, etc.)
    plan['nudges'].extend(build_nudges_for_plan(plan))

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

    debug_log('Tick complete')