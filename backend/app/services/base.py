"""Shared pieces for every AI provider.

- `AIService` is the interface the Planner talks to (Claude, Gemini, Ollama, demo).
- `JsonLLMService` implements all features for providers that return JSON text
  (Gemini, Ollama). A subclass only supplies `_json` and `_text`.
- `http_post` is the one place that does HTTP, so tests can swap in a fake.
"""

from __future__ import annotations

import json
import re
from typing import Awaitable, Callable, Literal, Protocol

from .. import prompts
from ..files import Attachment

Provider = Literal["claude", "gemini", "ollama", "demo"]


class AIError(Exception):
    """An AI call failed in a way the student should hear about."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


class AIService(Protocol):
    mode: Provider
    model: str | None
    label: str

    async def plan(self, assignment, ctx) -> dict: ...
    async def rebalance(self, sessions, assignments, ctx) -> dict: ...
    async def breakdown(self, session, assignment) -> list[str]: ...
    async def assess(self, *, history: list[dict], file: Attachment, user_text: str, today) -> dict: ...
    async def chat(self, *, history: list[dict], plan_summary: str, today) -> str: ...


# ---------- HTTP (injectable) ----------

HttpPost = Callable[[str, dict, dict, float], Awaitable[tuple[int, dict]]]


async def http_post(url: str, body: dict, headers: dict, timeout: float) -> tuple[int, dict]:
    """POST JSON and return (status, parsed body). Raises AIError if the server can't be reached."""
    import httpx  # imported here so the rest of the app (and tests) don't need it

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(url, json=body, headers=headers)
    except httpx.ConnectError as err:
        raise AIError(f"Can't connect to {url.split('/')[2]}. Is the service running?", 502) from err
    except httpx.TimeoutException as err:
        raise AIError("The AI service took too long to answer. Try again.", 504) from err
    try:
        data = res.json()
    except ValueError:
        data = {"raw": res.text[:500]}
    return res.status_code, data


# ---------- JSON helpers ----------


def parse_json_text(text: str):
    """Parse model output that should be JSON, tolerating code fences or a stray sentence."""
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except ValueError:
                pass
    raise AIError("The AI answer wasn't valid JSON. Try again.")


def json_instruction(tool: dict) -> str:
    return (
        f"\n\nTask: {tool['description']}\n"
        "Reply with only a JSON object (no markdown, no extra text) that matches this JSON Schema:\n"
        + json.dumps(tool["input_schema"])
    )


# ---------- base class for JSON-mode providers ----------


class JsonLLMService:
    """Implements every feature on top of two primitives a provider supplies."""

    mode: Provider
    model: str
    label: str

    async def _json(self, system: str, messages: list[dict], schema: dict, file: Attachment | None = None) -> dict:
        raise NotImplementedError

    async def _text(self, system: str, messages: list[dict]) -> str:
        raise NotImplementedError

    async def _ask_json(self, prompt: str, tool: dict, history: list[dict] | None = None, file: Attachment | None = None) -> dict:
        messages = [*(history or []), {"role": "user", "content": prompt + json_instruction(tool)}]
        out = await self._json(prompts.SYSTEM, messages, tool["input_schema"], file)
        if not isinstance(out, dict):
            raise AIError("The AI answer had the wrong shape. Try again.")
        return out

    async def plan(self, assignment, ctx) -> dict:
        return await self._ask_json(prompts.plan_prompt(assignment, ctx), prompts.PLAN_TOOL)

    async def rebalance(self, sessions, assignments, ctx) -> dict:
        return await self._ask_json(prompts.rebalance_prompt(sessions, assignments, ctx), prompts.REBALANCE_TOOL)

    async def breakdown(self, session, assignment) -> list[str]:
        out = await self._ask_json(prompts.breakdown_prompt(session, assignment), prompts.BREAKDOWN_TOOL)
        return out.get("steps", [])

    async def assess(self, *, history, file, user_text, today) -> dict:
        return await self._ask_json(prompts.assess_prompt(user_text, today), prompts.ASSESS_TOOL, history, file)

    async def chat(self, *, history, plan_summary, today) -> str:
        return (await self._text(prompts.chat_system(plan_summary, today), history)).strip()
