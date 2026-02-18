"""Match email senders to schedule fellow names using fellows.yaml and name fallback."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _normalize_name(s: str) -> str:
    """Lowercase and collapse spaces for comparison."""
    return " ".join(s.lower().split())


def sender_matches_fellow(
    email: str,
    display_name: str,
    fellow_name: str,
    fellow_aliases: List[str],
) -> bool:
    """
    Return True if (email, display_name) should be counted as this fellow.
    - Match if email or display_name is in fellow_aliases (from fellows.yaml).
    - Fallback: fellow_name appears in display_name or display_name in fellow_name (normalized).
    """
    email = email.lower().strip()
    display_name = display_name.strip()
    fellow_lower = _normalize_name(fellow_name)
    dn_lower = _normalize_name(display_name)

    for alias in fellow_aliases:
        alias = alias.strip().lower()
        if alias in (email, dn_lower):
            return True
        if email and alias in email:
            return True
        if dn_lower and alias in dn_lower:
            return True

    if not fellow_lower or not dn_lower:
        return False
    if fellow_lower in dn_lower or dn_lower in fellow_lower:
        return True
    # Last name, First name style: "Liu, Jerry" vs "Jerry Liu"
    parts_fellow = set(fellow_lower.split())
    parts_dn = set(dn_lower.replace(",", " ").split())
    if parts_fellow & parts_dn == parts_fellow:
        return True
    return False


def which_fellow(
    email: str,
    display_name: str,
    candidate_fellows: List[str],
    fellows_map: Dict[str, List[str]],
) -> Optional[str]:
    """
    If (email, display_name) matches one of candidate_fellows, return that fellow's name; else None.
    """
    for fellow in candidate_fellows:
        aliases = fellows_map.get(fellow, [])
        if sender_matches_fellow(email, display_name, fellow, aliases):
            return fellow
    return None


def mark_present(
    expected_list: List[Tuple[Any, ...]],  # (date, day_name, session_index, time, fellows)
    senders_by_date: Dict[Any, List[Tuple[str, str]]],  # date -> list of (email, display_name)
    fellows_map: Dict[str, List[str]],
) -> List[Tuple[Any, ...]]:
    """
    For each (date, day_name, session_index, time, fellows) in expected_list,
    determine which fellows are present based on senders for that date.
    Returns list of (date, day_name, session_index, time, fellow, status, matched_email)
    with status 'present' or 'absent'; matched_email is the sender email when present, None when absent.
    """
    from datetime import date
    report = []
    for (d, day_name, session_idx, time_slot, fellows) in expected_list:
        senders = senders_by_date.get(d, [])
        matched = {}  # fellow -> email (one email per fellow for display)
        for (email, display_name) in senders:
            fellow = which_fellow(email, display_name, fellows, fellows_map)
            if fellow and fellow not in matched:
                matched[fellow] = email
        for fellow in fellows:
            status = "present" if fellow in matched else "absent"
            report.append((
                d, day_name, session_idx, time_slot, fellow, status,
                matched.get(fellow),
            ))
    return report
