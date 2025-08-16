# Minimal CLI to test Alden calendar + planner + brain

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
from core.delivery import deliver_nudges
from core.audit import log_block_outcome
from learning.patterns import learn_preferences


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


def cmd_send_nudges(_args):
    """Build today's schedule and write to outbox (read-only delivery)."""
    plan = plan_day(get_today_events())
    sched = build_nudge_schedule(plan)
    written = deliver_nudges(sched)
    print(f"Outbox: wrote {written} nudge(s) to {CONFIG['delivery']['outbox_path']}")


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


def cmd_week_commit_anchors(args):
    wk = plan_week(args.start, days=args.days)
    msgs = materialize_weekly_anchors(wk)
    if msgs:
        print("Anchors created:")
        for m in msgs:
            print(f"- {m}")
    else:
        print("No anchors to create (check CONFIG.weekly_anchors).")


def cmd_audit_block(args):
    """Log an outcome for a planned block."""
    log_block_outcome(
        date_iso=args.date,
        title=args.title,
        planned_start_hhmm=args.start,
        planned_end_hhmm=args.end,
        outcome=args.outcome,
        actual_start_iso=args.actual_start,
        actual_end_iso=args.actual_end,
        notes=args.notes or ""
    )
    print("Recorded.")


def cmd_learn(_args):
    prefs = learn_preferences()
    print("Learned preferences:")
    print(prefs)


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

    sp = sub.add_parser("send-nudges", help="Write today's nudges to outbox (read-only delivery)")
    sp.set_defaults(func=cmd_send_nudges)

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

    sp = sub.add_parser("audit-block", help="Record outcome for a planned block")
    sp.add_argument("--date", required=True, help="YYYY-MM-DD (day of the block)")
    sp.add_argument("--title", required=True)
    sp.add_argument("--start", required=True, help="HH:MM planned start")
    sp.add_argument("--end", required=True, help="HH:MM planned end")
    sp.add_argument("--outcome", required=True, choices=["done", "partial", "skipped"])
    sp.add_argument("--actual-start", help="ISO timestamp when actually started (optional)")
    sp.add_argument("--actual-end", help="ISO timestamp when actually ended (optional)")
    sp.add_argument("--notes", help="Free text notes (optional)")
    sp.set_defaults(func=cmd_audit_block)

    sp = sub.add_parser("learn-preferences", help="Learn preferred time windows from audit log")
    sp.set_defaults(func=cmd_learn)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()