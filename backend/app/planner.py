"""Business logic behind each endpoint, independent of the web framework.

FastAPI wiring lives in main.py, so this class is unit-tested with a fake AI service.
"""

from __future__ import annotations

import logging
from datetime import date

from . import scheduler as sch
from .dates import date_range, parse_date, weekday
from .files import Upload, to_attachment
from .schemas import (
    Assessment, BreakdownRequest, BreakdownResponse, ChatPayload, ChatResponse, Health, MoveOut,
    PlannedSession, PlanRequest, PlanResponse, RebalanceRequest, RebalanceResponse,
)
from .services.base import AIError, AIService

log = logging.getLogger("studyease")


class BadRequest(ValueError):
    """Valid JSON that breaks a business rule; becomes a 400 response."""


def summarize_plan(assignments, sessions, today: date) -> str:
    if not assignments:
        return ""
    lines = []
    for a in assignments:
        mine = [s for s in sessions if s.assignment_id == a.id]
        left = [s for s in mine if not s.done]
        course = f" ({a.course})" if a.course else ""
        lines.append(f"- {a.title}{course}: {a.difficulty}, due {a.due} ({weekday(a.due)}), {len(left)} of {len(mine)} sessions left")
    todays = [f"{s.task} ({s.minutes} min)" for s in sessions if s.date == today and not s.done]
    return "\n".join(lines) + f"\nToday: {', '.join(todays) if todays else 'nothing scheduled'}"


def _history(messages) -> list[dict]:
    turns = [{"role": m.role, "content": m.content[:4000]} for m in messages if m.content.strip()][-12:]
    while turns and turns[0]["role"] != "user":  # the API needs a user turn first
        turns.pop(0)
    return turns


class Planner:
    def __init__(self, ai: AIService):
        self.ai = ai

    def health(self) -> Health:
        return Health(ai=self.ai.mode, model=self.ai.model, label=self.ai.label)

    async def plan(self, req: PlanRequest) -> PlanResponse:
        a = req.assignment
        if a.due < req.today:
            raise BadRequest("Pick a due date from today onward.")
        ctx = sch.PlanContext(req.today, req.daily, req.mood, sch.booked_by_date(req.sessions, a.id))

        source, note, warnings, sessions = "local", "", [], []
        if self.ai.mode != "demo":
            try:
                draft = await self.ai.plan(a, ctx)
                sessions, warnings = sch.normalize_plan(draft.get("sessions", []), a.due, a.hours, ctx)
                note = draft.get("note") if isinstance(draft.get("note"), str) else ""
                if sessions:
                    source = "ai"
            except Exception as err:  # any AI failure falls back to the local planner
                log.warning("AI plan failed, using local planner: %s", err)
                warnings.append(str(err))
        if source == "local":
            sessions = sch.local_plan(a.due, a.hours, a.difficulty, ctx)

        # Tell the student up front when the estimate can't fit before the due date.
        free = sum(max(0, ctx.daily - ctx.booked.get(d, 0)) for d in date_range(ctx.today, a.due))
        needed = round(a.hours * 60)
        if needed > free:
            warnings.append(
                f"This needs about {sch.format_minutes(needed)} but you only have {sch.format_minutes(free)} "
                "free before it's due, so some days will run over."
            )

        return PlanResponse(
            source=source, note=note, warnings=warnings,
            sessions=[PlannedSession(date=s.date, minutes=s.minutes, task=s.task, why=s.why) for s in sessions],
        )

    async def rebalance(self, req: RebalanceRequest) -> RebalanceResponse:
        ctx = sch.PlanContext(req.today, req.daily, req.mood)
        due_of = {a.id: a.due for a in req.assignments}
        if not any(not s.done for s in req.sessions):
            return RebalanceResponse(source="local", note="Nothing to rebalance yet.", moves=[])

        moves: list[sch.Move] | None = None
        note, source = "", "local"
        if self.ai.mode != "demo":
            try:
                out = await self.ai.rebalance(req.sessions, req.assignments, ctx)
                moves = [
                    sch.Move(str(m.get("id")), d, m.get("minutes"), str(m.get("why") or ""))
                    for m in out.get("moves", [])
                    if isinstance(m, dict) and (d := parse_date(m.get("date")))
                ]
                note, source = str(out.get("note") or ""), "ai"
            except Exception as err:
                log.warning("AI rebalance failed, using local rebalancer: %s", err)
        if moves is None:
            moves, note = sch.local_rebalance(req.sessions, due_of, ctx)

        # Whatever proposed the moves, only safe ones get through.
        accepted, n = sch.apply_moves(req.sessions, due_of, moves, req.today)
        current = {s.id: s for s in req.sessions}
        out_moves = [
            MoveOut(id=m.id, date=m.date, minutes=m.minutes, why=m.why)
            for m in accepted.values()
            if m.date != current[m.id].date or m.minutes != current[m.id].minutes
        ]
        if not note:
            note = f"Moved {len(out_moves)} sessions." if out_moves else "No changes needed."
        return RebalanceResponse(source=source, note=note, moves=out_moves)

    async def breakdown(self, req: BreakdownRequest) -> BreakdownResponse:
        session = req.session
        session.minutes = sch.round_minutes(session.minutes)
        steps: list = []
        try:
            steps = await self.ai.breakdown(session, req.assignment)
        except Exception as err:
            log.warning("AI breakdown failed: %s", err)
        clean = [s.strip()[:80] for s in steps if isinstance(s, str) and s.strip()][:6]
        if not clean:
            clean = ["Gather what you need", f"Work on: {session.task}"[:80], "Note where to pick up next time"]
        return BreakdownResponse(steps=clean)

    async def chat(self, payload: ChatPayload, upload: Upload | None) -> ChatResponse:
        history = _history(payload.messages)

        if upload is not None:
            file = to_attachment(upload)
            # The newest user message (if any) travels with the file, not as its own turn.
            user_text = history.pop()["content"] if history and history[-1]["role"] == "user" else ""
            result = await self.ai.assess(
                history=history, file=file, user_text=user_text, today=payload.today
            )
            return ChatResponse(reply=str(result.get("reply") or ""), assessment=_assessment(result, upload.filename, payload.today))

        if not history or history[-1]["role"] != "user":
            raise BadRequest("Send a message or upload a file.")
        reply = await self.ai.chat(
            history=history,
            plan_summary=summarize_plan(payload.assignments, payload.sessions, payload.today),
            today=payload.today,
        )
        return ChatResponse(reply=reply or "Sorry, I didn't catch that. Try asking another way.")


def _assessment(result: dict, filename: str, today: date) -> Assessment | None:
    difficulty = result.get("difficulty")
    if difficulty not in ("easy", "medium", "hard"):
        return None
    try:
        hours = float(result.get("estimated_hours"))
    except (TypeError, ValueError):
        hours = 2.0
    due = parse_date(result.get("due_date"))
    return Assessment(
        title=str(result.get("title") or filename)[:80],
        course=str(result.get("course") or "")[:20],
        difficulty=difficulty,
        hours=min(40.0, max(0.5, round(hours * 2) / 2)),
        due=due if due and due >= today else None,
        reasons=[str(r) for r in result.get("reasons") or []][:4],
        first_steps=[str(r) for r in result.get("first_steps") or []][:3],
    )


__all__ = ["Planner", "BadRequest", "AIError", "summarize_plan"]
