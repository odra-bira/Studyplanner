from datetime import date, timedelta
from types import SimpleNamespace as NS

from app.dates import parse_date
from app.scheduler import (
    Move, PlanContext, apply_moves, local_plan, local_rebalance, normalize_plan, round_minutes,
)

TODAY = date(2026, 10, 12)  # a Monday
DUE = date(2026, 10, 16)
D = lambda s: date.fromisoformat(s)  # noqa: E731


def ctx(**kw):
    return PlanContext(today=TODAY, daily=kw.pop("daily", 60), **kw)


def total(sessions):
    return sum(s.minutes for s in sessions)


def test_parse_date_rejects_impossible_dates():
    assert parse_date("2026-02-31") is None
    assert parse_date("10/12/2026") is None
    assert parse_date("2026-10-12") == TODAY


def test_round_minutes_clamps_to_15_180_in_steps_of_5():
    assert round_minutes(3) == 15
    assert round_minutes(62) == 60
    assert round_minutes(999) == 180
    assert round_minutes("abc") == 30


def test_normalize_pulls_dates_into_window_and_sorts():
    raw = [
        {"date": "2026-10-01", "minutes": 60, "task": "Outline"},
        {"date": "2026-10-20", "minutes": 60, "task": "Submit"},
        {"date": "2026-10-14", "minutes": 60, "task": "Draft"},
    ]
    sessions, _ = normalize_plan(raw, DUE, 3, ctx())
    assert all(TODAY <= s.date <= DUE for s in sessions)
    assert [s.task for s in sessions] == ["Outline", "Draft", "Submit"]


def test_normalize_rescales_totals_that_drift_from_estimate():
    raw = [{"date": "2026-10-13", "minutes": 180, "task": "A"}, {"date": "2026-10-14", "minutes": 180, "task": "B"}]
    sessions, warnings = normalize_plan(raw, DUE, 3, ctx(daily=240))
    assert abs(total(sessions) - 180) <= 18
    assert "Adjusted" in warnings[0]


def test_normalize_moves_sessions_off_full_days():
    booked = {D("2026-10-13"): 60}
    raw = [
        {"date": "2026-10-13", "minutes": 60, "task": "Outline"},
        {"date": "2026-10-15", "minutes": 60, "task": "Draft"},
        {"date": "2026-10-16", "minutes": 60, "task": "Review"},
    ]
    sessions, _ = normalize_plan(raw, DUE, 3, ctx(booked=booked))
    assert sessions[0].date != D("2026-10-13")
    per_day = dict(booked)
    for s in sessions:
        per_day[s.date] = per_day.get(s.date, 0) + s.minutes
    assert all(m <= 60 for m in per_day.values())


def test_normalize_drops_malformed_entries():
    sessions, warnings = normalize_plan([None, {"date": "soon", "task": "x"}, {"date": "2026-10-13"}], DUE, 3, ctx())
    assert sessions == []
    assert warnings


def test_local_plan_covers_estimate_and_ends_on_due_date():
    plan = local_plan(DUE, 3, "hard", ctx())
    assert plan[-1].date == DUE
    assert abs(total(plan) - 180) <= 30
    assert plan[0].task == "Outline and sources"
    assert all(TODAY <= s.date <= DUE for s in plan)


def test_local_plan_when_due_today():
    plan = local_plan(TODAY, 1, "hard", ctx())
    assert len(plan) == 1 and plan[0].date == TODAY


def _session(id, d, minutes=60, aid="a1", done=False):
    return NS(id=id, assignment_id=aid, date=d, minutes=minutes, done=done)


def test_local_rebalance_moves_missed_and_overloaded_sessions():
    sessions = [_session("s1", TODAY - timedelta(days=1)), _session("s2", TODAY), _session("s3", TODAY)]
    moves, _ = local_rebalance(sessions, {"a1": DUE}, ctx())
    accepted, _ = apply_moves(sessions, {"a1": DUE}, moves, TODAY)
    final = {s.id: accepted[s.id].date if s.id in accepted else s.date for s in sessions}
    assert all(d >= TODAY for d in final.values())
    per_day = {}
    for d in final.values():
        per_day[d] = per_day.get(d, 0) + 60
    assert all(m <= 60 for m in per_day.values())


def test_apply_moves_rejects_unsafe_moves():
    sessions = [_session("s1", D("2026-10-13")), _session("s2", D("2026-10-14"))]
    accepted, n = apply_moves(
        sessions,
        {"a1": DUE},
        [Move("s1", D("2026-10-20")), Move("s2", D("2026-10-12"))],  # past due; out of order
        TODAY,
    )
    assert n == 0 and accepted == {}
