"""Claude service built on the official Anthropic Python SDK.

Structured answers use forced tool use: Claude must "call" a tool whose input
schema is the JSON shape we want, so we never parse free text.
"""

from __future__ import annotations

import anthropic

from .. import prompts
from .base import AIError


class ClaudeService:
    mode = "claude"
    label = "Claude"

    def __init__(self, api_key: str, model: str, client: anthropic.AsyncAnthropic | None = None):
        self.model = model
        self.client = client or anthropic.AsyncAnthropic(api_key=api_key)

    async def _structured(self, messages: list[dict], tool: dict, max_tokens: int = 2048, system: str = prompts.SYSTEM) -> dict:
        try:
            res = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
            )
        except anthropic.APIError as err:
            raise _to_ai_error(err) from err
        for block in res.content:
            if block.type == "tool_use" and block.name == tool["name"]:
                return block.input
        raise AIError("Claude did not return a structured answer.")

    async def plan(self, assignment, ctx) -> dict:
        return await self._structured([{"role": "user", "content": prompts.plan_prompt(assignment, ctx)}], prompts.PLAN_TOOL)

    async def rebalance(self, sessions, assignments, ctx) -> dict:
        return await self._structured(
            [{"role": "user", "content": prompts.rebalance_prompt(sessions, assignments, ctx)}], prompts.REBALANCE_TOOL
        )

    async def breakdown(self, session, assignment) -> list[str]:
        out = await self._structured(
            [{"role": "user", "content": prompts.breakdown_prompt(session, assignment)}], prompts.BREAKDOWN_TOOL, max_tokens=512
        )
        return out.get("steps", [])

    async def assess(self, *, history, file, user_text, today) -> dict:
        """Upload turn: the file goes in as a document/image block next to the prompt."""
        messages = [
            *history,
            {"role": "user", "content": [file.anthropic_block(), {"type": "text", "text": prompts.assess_prompt(user_text, today)}]},
        ]
        return await self._structured(messages, prompts.ASSESS_TOOL, max_tokens=1500)

    async def chat(self, *, history, plan_summary, today) -> str:
        try:
            res = await self.client.messages.create(
                model=self.model,
                max_tokens=800,
                system=prompts.chat_system(plan_summary, today),
                messages=history,
            )
        except anthropic.APIError as err:
            raise _to_ai_error(err) from err
        return "\n".join(b.text for b in res.content if b.type == "text").strip()


def _to_ai_error(err: anthropic.APIError) -> AIError:
    status = getattr(err, "status_code", None)
    if status == 401:
        return AIError("The Anthropic API key is invalid. Check ANTHROPIC_API_KEY in backend/.env.", 500)
    if status == 429:
        return AIError("Claude is rate limited right now. Try again in a minute.", 429)
    if status == 400:
        return AIError(f"Claude rejected the request: {err.message}", 400)
    return AIError("Claude could not be reached. Try again.", 502)
