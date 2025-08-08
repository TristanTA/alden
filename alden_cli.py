# Minimal CLI to test Alden calendar + planner + brain
#
# Examples:
#   python alden_cli.py add "Study Session" 2025-08-09T10:00 --priority high --duration 90
#   python alden_cli.py list
#   python alden_cli.py today
#   python alden_cli.py plan
#   python alden_cli.py done "Study Session"
#   python alden_cli.py delete "Study Session"
#   python alden_cli.py update "Study Session" --time 2025-08-09T11:00 --duration 45

import argparse
from planning.daily_planner import plan_day

# If you renamed your calendar package, keep this aligned:
from alden_calendar.calendar import (
    add_event, list_events, get_today_events, delete_event, mark_done, update_event
)


def cmd_add(args):
    ev = add_event(
        args.title,
        args.time,
        category=args.category,
        priority=args.priority,
        duration_min=args.duration
    )
    print(f"Added: {ev['title']} @ {ev['time']} ({ev['duration_min']} min) "
          f"[{ev['priority']}] (id={ev['id']})")


def cmd_list(_args):
    for e in list_events():
        print(f"{e.get('time','?')} | {e.get('title')} "
              f"[{e.get('priority')}] {e.get('duration_min',60)}m "
              f"({e.get('status')}) id={e.get('id')}")


def cmd_today(_args):
    for e in get_today_events():
        print(f"{e.get('time','?')} | {e.get('title')} "
              f"[{e.get('priority')}] {e.get('duration_min',60)}m "
              f"({e.get('status')}) id={e.get('id')}")


def cmd_plan(_args):
    plan = plan_day(get_today_events())
    print("=== Plan ===")
    for b in plan["blocks"]:
        print(f"- {b['start']}–{b['end']}: {b['title']} [{b['priority']}] ({b['source']})")
    if plan["nudges"]:
        print("Nudges:")
        for n in plan["nudges"]:
            print(f"- {n}")


def cmd_done(args):
    updated = mark_done(args.id_or_title)
    if updated:
        print(f"Marked done: {updated.get('title')} (id={updated.get('id')})")
    else:
        print("No matching event found.")


def cmd_delete(args):
    ok = delete_event(args.id_or_title)
    print("Deleted." if ok else "No matching event found.")


def cmd_update(args):
    fields = {
        "title": args.title,
        "time": args.time,
        "priority": args.priority,
        "category": args.category,
        "duration_min": args.duration,
    }
    updated = update_event(args.id_or_title, **fields)
    if updated:
        print(f"Updated: {updated}")
    else:
        print("No matching event found.")


def main():
    p = argparse.ArgumentParser(description="Alden CLI")
    sub = p.add_subparsers(required=True)

    # add
    sp = sub.add_parser("add", help="Add an event")
    sp.add_argument("title")
    sp.add_argument("time", help="ISO time, e.g., 2025-08-09T10:00")
    sp.add_argument("--category", default="general")
    sp.add_argument("--priority", default="normal", choices=["low", "normal", "high"])
    sp.add_argument("--duration", type=int, default=60, help="Duration in minutes")
    sp.set_defaults(func=cmd_add)

    # list
    sp = sub.add_parser("list", help="List all events")
    sp.set_defaults(func=cmd_list)

    # today
    sp = sub.add_parser("today", help="List today's events")
    sp.set_defaults(func=cmd_today)

    # plan
    sp = sub.add_parser("plan", help="Generate today's plan")
    sp.set_defaults(func=cmd_plan)

    # done
    sp = sub.add_parser("done", help="Mark an event done (by id or exact title)")
    sp.add_argument("id_or_title")
    sp.set_defaults(func=cmd_done)

    # delete
    sp = sub.add_parser("delete", help="Delete an event (by id or exact title)")
    sp.add_argument("id_or_title")
    sp.set_defaults(func=cmd_delete)

    # update
    sp = sub.add_parser("update", help="Update an event (by id or exact title)")
    sp.add_argument("id_or_title")
    sp.add_argument("--title")
    sp.add_argument("--time")
    sp.add_argument("--priority", choices=["low", "normal", "high"])
    sp.add_argument("--category")
    sp.add_argument("--duration", type=int, help="Duration in minutes")
    sp.set_defaults(func=cmd_update)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()