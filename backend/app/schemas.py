"""Pydantic models: request validation and response shapes.

JSON uses camelCase (the React client's convention); Python code uses snake_case.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

Difficulty = Literal["easy", "medium", "hard"]
Mood = Literal["low", "medium", "high"]


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


class Assignment(Model):
    id: str = ""
    title: str = Field(min_length=1, max_length=80)
    course: str = Field(default="", max_length=20)
    due: date
    difficulty: Difficulty = "medium"
    hours: float = Field(gt=0, le=100)

    @field_validator("title", "course", mode="before")
    @classmethod
    def strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class Session(Model):
    id: str
    assignment_id: str = ""
    date: date
    minutes: int = Field(default=30, ge=0, le=600)
    task: str = Field(default="", max_length=200)
    done: bool = False


class PlannerContext(Model):
    today: date
    daily: int = Field(ge=15, le=720)
    mood: Mood | None = None


class PlanRequest(PlannerContext):
    assignment: Assignment
    sessions: list[Session] = []


class RebalanceRequest(PlannerContext):
    assignments: list[Assignment] = []
    sessions: list[Session] = []


class BreakdownSession(Model):
    task: str = Field(min_length=1, max_length=200)
    minutes: int = 30


class BreakdownRequest(Model):
    session: BreakdownSession
    assignment: Assignment | None = None


class ChatMessage(Model):
    role: Literal["user", "assistant"]
    content: str


class ChatPayload(Model):
    today: date
    messages: list[ChatMessage] = []
    assignments: list[Assignment] = []
    sessions: list[Session] = []


# ---------- responses ----------


class PlannedSession(Model):
    date: date
    minutes: int
    task: str
    why: str = ""


class PlanResponse(Model):
    source: Literal["ai", "local"]
    note: str = ""
    warnings: list[str] = []
    sessions: list[PlannedSession]


class MoveOut(Model):
    id: str
    date: date
    minutes: int
    why: str = ""


class RebalanceResponse(Model):
    source: Literal["ai", "local"]
    note: str
    moves: list[MoveOut]


class BreakdownResponse(Model):
    steps: list[str]


class Assessment(Model):
    title: str
    course: str = ""
    difficulty: Difficulty
    hours: float
    due: date | None = None
    reasons: list[str] = []
    first_steps: list[str] = []


class ChatResponse(Model):
    reply: str
    assessment: Assessment | None = None


class Health(Model):
    ok: bool = True
    ai: Literal["claude", "gemini", "ollama", "demo"]
    model: str | None = None
    label: str = ""
