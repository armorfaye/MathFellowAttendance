#!/usr/bin/env python3
"""
Math Fellow Attendance: check who submitted attendance photos via email.
Usage: python attendance.py --week blue [--off YYYY-MM-DD ...] [--start DATE] [--end DATE] [--output FILE]
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Tuple

from config import (
    get_expected_attendance,
    load_fellows,
    load_schedule,
)
from gmail_client import (
    build_service,
    get_senders_for_date,
    get_senders_without_image_for_date,
)
from matching import mark_present


def _week_sunday_to_saturday(ref: date) -> Tuple[date, date]:
    """Return (start, end) for the week containing ref (Sunday--Saturday)."""
    # Python weekday: Monday=0, Sunday=6
    days_back = (ref.weekday() + 1) % 7
    if ref.weekday() == 6:
        days_back = 0
    start = ref - timedelta(days=days_back)
    end = start + timedelta(days=6)
    return start, end


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check Math Fellow attendance from emails to mathcenter@peddie.org"
    )
    parser.add_argument(
        "--week",
        required=True,
        choices=["blue", "gold"],
        help="Week type: blue or gold",
    )
    parser.add_argument(
        "--off",
        nargs="*",
        default=[],
        metavar="DATE",
        help="Dates that are off (holidays), e.g. --off 2025-02-20 2025-03-01",
    )
    parser.add_argument(
        "--start",
        type=_parse_date,
        default=None,
        metavar="YYYY-MM-DD",
        help="Start of date range (default: Sunday of current week)",
    )
    parser.add_argument(
        "--end",
        type=_parse_date,
        default=None,
        metavar="YYYY-MM-DD",
        help="End of date range (default: Saturday of current week)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write CSV report to this file (default: print only)",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing schedule.yaml, fellows.yaml, credentials.json",
    )
    args = parser.parse_args()

    off_dates = {_parse_date(d) for d in args.off}
    today = date.today()
    start = args.start
    end = args.end
    if start is None or end is None:
        start, end = _week_sunday_to_saturday(today)
    if start > end:
        start, end = end, start

    config_dir = args.config_dir
    schedule = load_schedule(config_dir)
    fellows_map = load_fellows(config_dir)
    expected = get_expected_attendance(schedule, args.week, start, end, off_dates)

    if not expected:
        print("No sessions in the given date range (or all days are off).")
        return

    service = build_service(config_dir)
    dates_to_fetch = {t[0] for t in expected}
    senders_by_date = {}
    no_image_senders_by_date = {}
    for d in sorted(dates_to_fetch):
        senders_by_date[d] = get_senders_for_date(service, d)
        no_image_senders_by_date[d] = get_senders_without_image_for_date(service, d)

    report = mark_present(expected, senders_by_date, fellows_map)

    # Console summary
    print(f"Week: {args.week} | Range: {start} to {end}")
    if off_dates:
        print(f"Days off: {', '.join(str(d) for d in sorted(off_dates))}")
    print()

    current_key = None
    for (d, day_name, session_idx, time_slot, fellow, status, matched_email) in report:
        key = (d, day_name, session_idx)
        if key != current_key:
            current_key = key
            session_label = f"Session {session_idx + 1}"
            print(f"{d} {day_name} {session_label} ({time_slot})")
        symbol = "✓" if status == "present" else "✗"
        email_part = f" ({matched_email})" if matched_email else ""
        print(f"  {symbol} {fellow}: {status}{email_part}")
    print()

    # Per-session summary
    by_session = defaultdict(lambda: {"present": 0, "absent": 0, "names": []})
    for (d, day_name, session_idx, time_slot, fellow, status, _) in report:
        k = (d, day_name, session_idx, time_slot)
        by_session[k]["names"].append((fellow, status))
        if status == "present":
            by_session[k]["present"] += 1
        else:
            by_session[k]["absent"] += 1
    print("Summary:")
    for (d, day_name, session_idx, time_slot), counts in sorted(by_session.items()):
        total = counts["present"] + counts["absent"]
        absent_names = [f for f, s in counts["names"] if s == "absent"]
        line = f"  {d} {day_name} Session {session_idx + 1}: {counts['present']}/{total} present"
        if absent_names:
            line += f" (absent: {', '.join(absent_names)})"
        print(line)

    # Possible excuse emails (no image attached)
    any_no_image = any(no_image_senders_by_date.get(d) for d in sorted(dates_to_fetch))
    if any_no_image:
        print("\nPossible excuse emails (no image attached):")
        for d in sorted(dates_to_fetch):
            senders = no_image_senders_by_date.get(d, [])
            if senders:
                for email, display_name in senders:
                    who = f"{display_name} <{email}>" if display_name else email
                    print(f"  {d}: {who}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "day", "session", "time", "fellow", "status", "email"])
            for row in report:
                d, day_name, session_idx, time_slot, fellow, status, matched_email = row
                w.writerow([d, day_name, session_idx + 1, time_slot, fellow, status, matched_email or ""])
        print(f"\nReport written to {args.output}")


if __name__ == "__main__":
    main()
