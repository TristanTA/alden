# Minimal CLI to test Alden calendar + planner + brain
#
# Subcommands:
#   add           → add an event
#   list          → list all events
#   today         → list today's events
#   plan          → print today's plan (no write-back)
#   plan-commit   → plan + apply reschedules (+ optional focus blocks)
#   done          → mark event done
#   delete        → delete event
#   update        → update event fields
#
# Examples:
#   python alden_cli.py add "Study Session" 2025-08-09T10:00 --priority high --duration 90
#   python alden_cli.py plan
#   python alden_cli.py plan-commit --enable-writeback --materialize-focus
#   python alden_cli.py update "Study Session" --time 2025-08-09T11:00 --duration 45

import argparse
from planning.daily_planner import plan_day
from utils.config import CONFIG

# Adjust if you renamed your calendar package differently:
from alden_calendar.calendar import (
    add_event, list_events, get_today_events, delete_event, mark_done, update_event
)

# Write-back helpers:
from core.writeback import apply_reschedules, materialize_focus_blocks


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


def _print_plan(plan: dict):
    print("=== Plan ===")
    for b in plan["blocks"]:
        print(f"- {b['start']}–{b['end']}: {b['title']} [{b['priority']}] ({b['source']})")
    if plan["nudges"]:
        print("Nudges:")
        for n in plan["nudges"]:
            print(f"- {n}")
    # Show prospective write-back counts
    print(f"\n[Info] Reschedules suggested: {len(plan.get('reschedules', []))}")
    print(f"[Info] Focus gaps detected:  {len(plan.get('focus_blocks', []))}")


def cmd_plan(_args):
    plan = plan_day(get_today_events())
    _print_plan(plan)


def cmd_plan_commit(args):
    """Generate today's plan and write it back based on flags/config."""
    plan = plan_day(get_today_events())
    _print_plan(plan)

    # Determine effective write-back settings (CLI flags override config)
    wb_cfg = CONFIG.get("write_back", {})
    do_resched = args.enable_writeback or wb_cfg.get("enabled", False)
    do_focus   = args.materialize_focus or (wb_cfg.get("enabled", False) and wb_cfg.get("materialize_focus_blocks", False))

    print("\n=== Write-back ===")
    if not (do_resched or do_focus):
        print("Write-back is disabled (enable with --enable-writeback and/or --materialize-focus).")
        return

    if do_resched:
        msgs = apply_reschedules(plan.get("reschedules", []))
        if msgs:
            print("Reschedules applied:")
            for m in msgs:
                print(f"- {m}")
        else:
            print("No reschedules to apply.")

    if do_focus:
        msgs = materialize_focus_blocks(plan.get("focus_blocks", []))
        if msgs:
            print("Focus blocks created:")
            for m in msgs:
                print(f"- {m}")
        else:
            print("No focus blocks to create.")

    print("Write-back complete.")


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

    # plan (no write-back)
    sp = sub.add_parser("plan", help="Generate today's plan (no write-back)")
    sp.set_defaults(func=cmd_plan)

    # plan-commit (write-back path)
    sp = sub.add_parser("plan-commit", help="Plan + commit reschedules (+ optional focus blocks)")
    sp.add_argument("--enable-writeback", action="store_true",
                    help="Apply reschedules even if config write_back.enabled is False.")
    sp.add_argument("--materialize-focus", action="store_true",
                    help="Create focus block events for gaps (overrides config for this run).")
    sp.set_defaults(func=cmd_plan_commit)

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