"""The scheduling core: pure functions, no I/O, fully unit-tested.

The AI drafts a plan, but a language model can return dates outside the allowed
window, sessions that ignore the student's daily limit, or totals that drift
from the time estimate. `normalize_plan` checks and repairs every AI draft
before the student sees it. `local_plan` and `local_rebalance` are
deterministic fallbacks for when no API key is set or the AI call fails.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

from .dates import date_range, parse_date, weekday

MIN_SESSION = 15
MAX_SESSION = 180

PHASES = {
    "easy": ["Work through it", "Check and submit"],
    "medium": ["Gather materials and outline", "Main work session", "Review and submit"],
    "hard": ["Outline and sources", "First draft", "Revise the draft", "Review and submit"],
}


@dataclass
class PlanContext:
    today: date
    daily: int
    mood: str | None = None
    booked: dict[date, int] = field(default_factory=dict)


@dataclass
class DraftSession:
    date: date
    minutes: int
    task: str
    why: str = ""


def round_minutes(value) -> int:
    """Clamp to 15..180 minutes in steps of 5."""
    try:
        n = int(round(float(value) / 5) * 5)
    except (TypeError, ValueError):
        n = 0
    return min(MAX_SESSION, max(MIN_SESSION, n or 30))


def format_minutes(m: int) -> str:
    if m < 60:
        return f"{m} min"
    return f"{m // 60}h {m % 60}m" if m % 60 else f"{m // 60}h"


def booked_by_date(sessions, except_assignment_id: str | None = None) -> dict[date, int]:
    """Minutes already planned per date, ignoring finished sessions and (optionally) one assignment."""
    booked: dict[date, int] = {}
    for s in sessions:
        if s.done or s.assignment_id == except_assignment_id:
            continue
        booked[s.date] = booked.get(s.date, 0) + s.minutes
    return booked


def session_cap(daily: int, mood: str | None) -> int:
    """A "high" stress check-in keeps sessions short."""
    return min(daily, 45) if mood == "high" else daily


def normalize_plan(raw: list, due: date, hours: float, ctx: PlanContext) -> tuple[list[DraftSession], list[str]]:
    """Validate and repair an AI-drafted plan for one assignment."""
    booked = dict(ctx.booked)
    warnings: list[str] = []
    target = round(hours * 60)

    # 1. Keep well-formed entries and pull dates into the allowed window.
    sessions: list[DraftSession] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        d = parse_date(item.get("date"))
        task = item.get("task")
        if d is None or not isinstance(task, str) or not task.strip():
            continue
        d = max(ctx.today, min(due, d))
        why = item.get("why") if isinstance(item.get("why"), str) else ""
        sessions.append(DraftSession(d, round_minutes(item.get("minutes")), task.strip()[:80], why.strip()[:200]))

    if not sessions:
        return [], ["The AI plan was empty."]

    # 2. Keep the total within 10% of the student's own estimate.
    total = sum(s.minutes for s in sessions)
    if abs(total - target) > target * 0.1:
        factor = target / total
        for s in sessions:
            s.minutes = round_minutes(s.minutes * factor)
        warnings.append(f"Adjusted session lengths to match your {format_minutes(target)} estimate.")

    # 3. Chronological order (Python's sort is stable, so same-day steps keep their order).
    sessions.sort(key=lambda s: s.date)

    # 4. Respect the daily limit: move a session to the nearest day with room,
    #    never before the previous step and never after the due date.
    floor = ctx.today
    for s in sessions:
        s.date = max(s.date, floor)
        if booked.get(s.date, 0) + s.minutes > ctx.daily:
            candidates = sorted(date_range(floor, due), key=lambda d: (abs((d - s.date).days), d))
            free = next((d for d in candidates if booked.get(d, 0) + s.minutes <= ctx.daily), None)
            if free and free != s.date:
                note = f"Moved to {weekday(free)} to fit your daily time."
                s.why = f"{s.why} ({note})" if s.why else note
                s.date = free
            elif free is None:
                warnings.append(f"{weekday(s.date)} runs over your {format_minutes(ctx.daily)} limit.")
        booked[s.date] = booked.get(s.date, 0) + s.minutes
        floor = s.date

    sessions.sort(key=lambda s: s.date)
    return sessions, list(dict.fromkeys(warnings))


def local_plan(due: date, hours: float, difficulty: str, ctx: PlanContext) -> list[DraftSession]:
    """Deterministic planner used without an API key, or when the AI call fails."""
    days = date_range(ctx.today, due)
    total = round(hours * 60)
    cap = session_cap(ctx.daily, ctx.mood)
    phases = PHASES.get(difficulty, PHASES["medium"])

    n = max(math.ceil(total / max(MIN_SESSION, cap)), min(len(phases), len(days)))
    n = max(1, min(n, len(days)))

    # The final pass lands on the due date; earlier sessions prefer days with free time.
    others = [d for d in days if d != due]
    others.sort(key=lambda d: (ctx.daily - ctx.booked.get(d, 0) <= 0, d))
    chosen = {due}
    step = len(others) / max(1, n - 1)
    for k in range(n - 1):
        if not others:
            break
        chosen.add(others[min(len(others) - 1, int(k * step))])
    dates = sorted(chosen)

    per = round_minutes(total / len(dates))
    plan = []
    for i, d in enumerate(dates):
        task = phases[min(len(phases) - 1, i * len(phases) // len(dates))]
        free = ctx.daily - ctx.booked.get(d, 0)
        if i == len(dates) - 1:
            why = "Final pass lands on the due date so nothing is left to chance."
        elif free >= per:
            why = f"Fits in your {format_minutes(ctx.daily)} on {weekday(d)} with {format_minutes(free - per)} to spare."
        else:
            why = f"{weekday(d)} is already busy; consider moving this or trimming the estimate."
        plan.append(DraftSession(d, per, task, why))
    return plan


@dataclass
class Move:
    id: str
    date: date
    minutes: int | None = None
    why: str = ""


def _in_order(dates: list[date]) -> bool:
    return all(dates[i] >= dates[i - 1] for i in range(1, len(dates)))


def apply_moves(sessions, due_of: dict[str, date], moves: list[Move], today: date) -> tuple[dict[str, Move], int]:
    """Accept only safe moves.

    A move is dropped if it lands before today or after the due date. If the
    accepted moves leave an assignment's steps out of order, all of that
    assignment's moves are undone. Returns the accepted moves by session id.
    """
    by_id = {s.id: s for s in sessions}
    accepted: dict[str, Move] = {}
    for m in moves:
        s = by_id.get(m.id)
        if s is None or s.done:
            continue
        due = due_of.get(s.assignment_id)
        if m.date < today or (due and m.date > due):
            continue
        accepted[m.id] = Move(m.id, m.date, round_minutes(m.minutes) if m.minutes else s.minutes, m.why[:200])

    # Check order per assignment with the moves applied.
    for aid in {by_id[i].assignment_id for i in accepted}:
        mine = [s for s in sessions if s.assignment_id == aid and not s.done]
        dates = [accepted[s.id].date if s.id in accepted else s.date for s in mine]
        if not _in_order(dates):
            for s in mine:
                accepted.pop(s.id, None)
    return accepted, len(accepted)


def local_rebalance(sessions, due_of: dict[str, date], ctx: PlanContext) -> tuple[list[Move], str]:
    """Greedy rebalancer: earliest-due first, move sessions off overloaded or past days."""
    load: dict[date, int] = {}
    last: dict[str, date] = {}
    moves: list[Move] = []

    open_sessions = [(i, s) for i, s in enumerate(sessions) if not s.done]
    open_sessions.sort(key=lambda p: (due_of.get(p[1].assignment_id, date.max), p[0]))

    for _, s in open_sessions:
        due = due_of.get(s.assignment_id, s.date)
        floor = max(ctx.today, last.get(s.assignment_id, ctx.today))
        d = max(s.date, floor)
        if load.get(d, 0) + s.minutes > ctx.daily:
            free = next((x for x in date_range(floor, due) if load.get(x, 0) + s.minutes <= ctx.daily), None)
            if free:
                d = free
        load[d] = load.get(d, 0) + s.minutes
        last[s.assignment_id] = d
        if d != s.date:
            moves.append(Move(s.id, d, s.minutes, f"Moved to {weekday(d)} to stay within {format_minutes(ctx.daily)}."))

    over = any(m > ctx.daily for m in load.values())
    if moves:
        note = f"Moved {len(moves)} session{'s' if len(moves) > 1 else ''}."
    else:
        note = "" if over else "Your week already fits."
    if over:
        note = f"{note} Some days still run over; trim an estimate or raise your daily time.".strip()
    return moves, note
