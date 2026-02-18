"""Load schedule and fellow mapping; compute expected attendance for a date range."""

from __future__ import annotations

import yaml
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Session days (lowercase) and their weekday numbers (Monday=0 in Python)
DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
SESSION_DAYS = {"sunday", "tuesday", "thursday"}


def load_schedule(config_dir: Path) -> dict:
    """Load schedule.yaml from config_dir."""
    path = config_dir / "schedule.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Schedule not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def load_fellows(config_dir: Path) -> Dict[str, List[str]]:
    """Load fellows.yaml (name -> list of emails/aliases). Returns {} if missing."""
    path = config_dir / "fellows.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f)
    if not data:
        return {}
    # Normalize: allow single string or list
    out = {}
    for name, vals in data.items():
        if vals is None:
            out[name] = []
        elif isinstance(vals, list):
            out[name] = [str(v).strip().lower() for v in vals]
        else:
            out[name] = [str(vals).strip().lower()]
    return out


def get_expected_attendance(
    schedule: dict,
    week_type: str,
    start_date: date,
    end_date: date,
    off_dates: Set[date],
) -> List[Tuple[date, str, int, str, List[str]]]:
    """
    Return list of (date, day_name, session_index, time, fellows) for which we expect attendance.
    Only includes session days (sunday, tuesday, thursday) and excludes off_dates.
    """
    if week_type not in schedule:
        raise ValueError(f"Unknown week type: {week_type}. Use 'blue' or 'gold'.")
    week = schedule[week_type]
    result = []
    d = start_date
    while d <= end_date:
        if d in off_dates:
            d += timedelta(days=1)
            continue
        day_name = DAY_NAMES[d.weekday()]
        if day_name not in SESSION_DAYS:
            d += timedelta(days=1)
            continue
        if day_name not in week:
            d += timedelta(days=1)
            continue
        sessions = week[day_name]
        for idx, session in enumerate(sessions):
            time_slot = session.get("time", "")
            fellows = session.get("fellows", [])
            result.append((d, day_name, idx, time_slot, list(fellows)))
        d += timedelta(days=1)
    return result
