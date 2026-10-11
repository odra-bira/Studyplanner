import asyncio
from datetime import date

import pytest

from app.files import Upload, UploadError
from app.planner import BadRequest, Planner
from app.schemas import ChatPayload, PlanRequest, RebalanceRequest
from app.services.demo import DemoService

BASE = {"today": "2026-10-12", "daily": 60}
ASSIGNMENT = {"id": "a1", "title": "Lab report", "course": "BIO 201", "due": "2026-10-16", "difficulty": "hard", "hours": 3}


class FakeClaude:
    """Stands in for ClaudeService; returns canned answers."""

    mode = "claude"
    model = "fake"
    label = "Fake"

    def __init__(self, **answers):
        self.answers = answers
        self.calls = {}

    async def plan(self, assignment, ctx):
        return self._answer("plan")

    async def rebalance(self, sessions, assignments, ctx):
        return self._answer("rebalance")

    async def breakdown(self, session, assignment):
        return self._answer("breakdown")

    async def assess(self, **kw):
        self.calls["assess"] = kw
        return self._answer("assess")

    async def chat(self, **kw):
        self.calls["chat"] = kw
        return self._answer("chat")

    def _answer(self, name):
        a = self.answers[name]
        if isinstance(a, Exception):
            raise a
        return a


def run(coro):
    return asyncio.run(coro)


def test_plan_uses_ai_draft_after_repairing_it():
    ai = FakeClaude(plan={
        "note": "Three sessions.",
        "sessions": [
            {"date": "2026-10-01", "minutes": 60, "task": "Outline", "why": "early"},  # before today
            {"date": "2026-10-14", "minutes": 60, "task": "Draft", "why": "mid"},
            {"date": "2026-10-16", "minutes": 60, "task": "Submit", "why": "end"},
        ],
    })
    out = run(Planner(ai).plan(PlanRequest.model_validate({**BASE, "assignment": ASSIGNMENT})))
    assert out.source == "ai"
    assert out.sessions[0].date == date(2026, 10, 12)
    assert out.note == "Three sessions."


def test_plan_falls_back_when_ai_fails():
    ai = FakeClaude(plan=RuntimeError("Claude could not be reached."))
    out = run(Planner(ai).plan(PlanRequest.model_validate({**BASE, "assignment": ASSIGNMENT})))
    assert out.source == "local"
    assert out.sessions
    assert "Claude could not be reached." in out.warnings


def test_plan_warns_when_estimate_cannot_fit():
    big = {**ASSIGNMENT, "hours": 20}
    out = run(Planner(DemoService()).plan(PlanRequest.model_validate({**BASE, "assignment": big})))
    assert any("only have" in w for w in out.warnings)


def test_plan_rejects_past_due_date():
    req = PlanRequest.model_validate({**BASE, "assignment": {**ASSIGNMENT, "due": "2026-10-01"}})
    with pytest.raises(BadRequest):
        run(Planner(DemoService()).plan(req))


def test_rebalance_only_applies_safe_ai_moves():
    sessions = [
        {"id": "s1", "assignmentId": "a1", "date": "2026-10-12", "minutes": 60, "task": "A"},
        {"id": "s2", "assignmentId": "a1", "date": "2026-10-12", "minutes": 60, "task": "B"},
    ]
    ai = FakeClaude(rebalance={"note": "Moved B.", "moves": [
        {"id": "s2", "date": "2026-10-13", "why": "room"},
        {"id": "s1", "date": "2026-10-30"},  # past due: dropped
    ]})
    req = RebalanceRequest.model_validate({**BASE, "assignments": [ASSIGNMENT], "sessions": sessions})
    out = run(Planner(ai).rebalance(req))
    assert [(m.id, m.date.isoformat()) for m in out.moves] == [("s2", "2026-10-13")]


def test_chat_upload_returns_assessment_in_demo_mode():
    text = b"BIO 201 Lab Report\nWrite a 10 page lab report with statistical analysis and 8 peer-reviewed sources. Due 2026-10-20."
    payload = ChatPayload.model_validate({"today": "2026-10-12", "messages": [{"role": "user", "content": "How hard is this?"}]})
    out = run(Planner(DemoService()).chat(payload, Upload(text, "text/plain", "lab.txt")))
    a = out.assessment
    assert a.difficulty == "hard"
    assert a.course == "BIO 201"
    assert a.due == date(2026, 10, 20)
    assert a.hours >= 5


def test_chat_sends_pdf_to_claude_as_document_block():
    ai = FakeClaude(assess={"reply": "Medium.", "title": "Essay", "course": "", "difficulty": "medium",
                            "estimated_hours": 4, "due_date": None, "reasons": ["r"], "first_steps": ["s"]})
    payload = ChatPayload.model_validate({"today": "2026-10-12", "messages": [{"role": "user", "content": "rate it"}]})
    out = run(Planner(ai).chat(payload, Upload(b"%PDF-1.4 fake", "application/pdf", "essay.pdf")))
    call = ai.calls["assess"]
    assert call["file"].kind == "pdf"
    assert call["file"].anthropic_block()["type"] == "document"
    assert call["user_text"] == "rate it"
    assert call["history"] == []
    assert out.assessment.hours == 4


def test_chat_rejects_unsupported_files():
    payload = ChatPayload.model_validate({"today": "2026-10-12"})
    with pytest.raises(UploadError):
        run(Planner(DemoService()).chat(payload, Upload(b"PK..", "application/zip", "a.zip")))


def test_chat_without_message_or_file_is_rejected():
    payload = ChatPayload.model_validate({"today": "2026-10-12", "messages": []})
    with pytest.raises(BadRequest):
        run(Planner(DemoService()).chat(payload, None))
