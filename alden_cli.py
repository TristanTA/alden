# Minimal CLI to test Alden calendar + planner + brain
#
# Subcommands:
#   add               → add an event
#   list              → list all events
#   today             → list today's events
#   plan              → print today's plan (no write-back)
#   plan-commit       → plan + apply reschedules (+ optional focus blocks)
#   nudge-schedule    → print timestamped nudges for today's plan
#   week              → print a multi-day weekly outline
#   week-commit-anchors → create weekly anchor focus events per config
#   done              → mark event done
#   delete            → delete event
#   update            → update event fields

import argparse
from planning.daily_planner import plan_day
from planning.weekly_planner import plan_week
from utils.config import CONFIG

# Adjust if you renamed your calendar package differently:
from alden_calendar.calendar import (
    add_event, list_events, get_today_events, delete_event, mark_done, update_event
)

from core.writeback import apply_reschedules, materialize_focus_blocks, materialize_weekly_anchors
from core.notifications import build_nudge_schedule


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
    print(f"\n[Info] Reschedules suggested: {len(plan.get('reschedules', []))}")
    print(f"[Info] Focus gaps detected:  {len(plan.get('focus_blocks', []))}")


def cmd_plan(_args):
    plan = plan_day(get_today_events())
    _print_plan(plan)


def cmd_nudge_schedule(_args):
    plan = plan_day(get_today_events())
    sched = build_nudge_schedule(plan)
    print("=== Nudge Schedule (timestamped) ===")
    for n in sched:
        print(f"{n['at']}  [{n['type']}]  {n['message']}")


def cmd_plan_commit(args):
    plan = plan_day(get_today_events())
    _print_plan(plan)

    wb_cfg = CONFIG.get("write_back", {})
    do_resched = args.enable_writeback or wb_cfg.get("enabled", False)
    do_focus   = args.materialize_focus or (wb_cfg.get("enabled", False) and wb_cfg.get("materialize_focus_blocks", False))

    resched_count = 0
    focus_count = 0

    print("\n=== Write-back ===")
    if not (do_resched or do_focus):
        print("Write-back is disabled (enable with --enable-writeback and/or --materialize-focus).")
        return

    if do_resched:
        msgs = apply_reschedules(plan.get("reschedules", []))
        resched_count = len(msgs)
        if msgs:
            print("Reschedules applied:")
            for m in msgs:
                print(f"- {m}")
        else:
            print("No reschedules to apply.")

    if do_focus:
        msgs = materialize_focus_blocks(plan.get("focus_blocks", []))
        focus_count = len(msgs)
        if msgs:
            print("Focus blocks created:")
            for m in msgs:
                print(f"- {m}")
        else:
            print("No focus blocks to create.")

    print(f"\n[Summary] {resched_count} events rescheduled, {focus_count} focus blocks created.")
    print("Write-back complete.")


def cmd_week(args):
    wk = plan_week(args.start, days=args.days)
    print(f"=== Weekly Outline (start={args.start or 'today'}, days={args.days}) ===")
    for d in wk["days"]:
        date = d["date"]
        summ = d["summary"]
        print(f"\n{date}  —  events: {summ['events']}  "
              f"(high:{summ['high']} normal:{summ['normal']} low:{summ['low']})  "
              f"scheduled:{summ['scheduled_minutes']}m  "
              f"focus:{summ['focus_minutes']}m  free:{summ['free_minutes']}m")
        for b in d["plan"]["blocks"]:
            print(f"  - {b['start']}–{b['end']}: {b['title']} [{b['priority']}] ({b['source']})")
        if d.get("anchor_suggestions"):
            print("  Anchors:")
            for a in d["anchor_suggestions"]:
                print(f"    • {a['start']}–{a['end']}: {a['title']} [{a.get('priority','normal')}]")
    t = wk["totals"]
    print("\nTotals:",
          f"events:{t['events']}, high:{t['high']}, normal:{t['normal']}, low:{t['low']},",
          f"scheduled:{t['scheduled_minutes']}m, focus:{t['focus_minutes']}m, free:{t['free_minutes']}m")


def cmd_week_commit_anchors(args):
    wk = plan_week(args.start, days=args.days)
    msgs = materialize_weekly_anchors(wk)
    if msgs:
        print("Anchors created:")
        for m in msgs:
            print(f"- {m}")
    else:
        print("No anchors to create (check CONFIG.weekly_anchors).")


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

    sp = sub.add_parser("add", help="Add an event")
    sp.add_argument("title")
    sp.add_argument("time", help="ISO time, e.g., 2025-08-09T10:00")
    sp.add_argument("--category", default="general")
    sp.add_argument("--priority", default="normal", choices=["low", "normal", "high"])
    sp.add_argument("--duration", type=int, default=60, help="Duration in minutes")
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("list", help="List all events")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("today", help="List today's events")
    sp.set_defaults(func=cmd_today)

    sp = sub.add_parser("plan", help="Generate today's plan (no write-back)")
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser("nudge-schedule", help="Build timestamped nudges for today's plan")
    sp.set_defaults(func=cmd_nudge_schedule)

    sp = sub.add_parser("plan-commit", help="Plan + commit reschedules (+ optional focus blocks)")
    sp.add_argument("--enable-writeback", action="store_true",
                    help="Apply reschedules even if config write_back.enabled is False.")
    sp.add_argument("--materialize-focus", action="store_true",
                    help="Create focus block events for gaps (overrides config for this run).")
    sp.set_defaults(func=cmd_plan_commit)

    sp = sub.add_parser("week", help="Generate a multi-day outline")
    sp.add_argument("--start", help="YYYY-MM-DD (defaults to today)")
    sp.add_argument("--days", type=int, default=7, help="Number of days (default 7)")
    sp.set_defaults(func=cmd_week)

    sp = sub.add_parser("week-commit-anchors", help="Create weekly anchor events based on config")
    sp.add_argument("--start", help="YYYY-MM-DD (defaults to today)")
    sp.add_argument("--days", type=int, default=7, help="Number of days (default 7)")
    sp.set_defaults(func=cmd_week_commit_anchors)

    sp = sub.add_parser("done", help="Mark an event done (by id or exact title)")
    sp.add_argument("id_or_title")
    sp.set_defaults(func=cmd_done)

    sp = sub.add_parser("delete", help="Delete an event (by id or exact title)")
    sp.add_argument("id_or_title")
    sp.set_defaults(func=cmd_delete)

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