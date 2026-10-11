"""Google Gemini over its REST API (free tier available for Flash models).

Get a key at https://aistudio.google.com/apikey and set GEMINI_API_KEY.
Gemini reads PDFs and images directly, and `responseSchema` makes it return
JSON in the shape we ask for.
"""

from __future__ import annotations

from ..files import Attachment
from .base import AIError, HttpPost, JsonLLMService, http_post, parse_json_text

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"


def to_gemini_schema(schema: dict) -> dict:
    """Convert our JSON Schema to Gemini's OpenAPI-style schema (uppercase types, `nullable`)."""
    out: dict = {}
    t = schema.get("type")
    if isinstance(t, list):  # e.g. ["string", "null"]
        non_null = [x for x in t if x != "null"]
        t = non_null[0] if non_null else "string"
        out["nullable"] = True
    if t:
        out["type"] = t.upper()
    for key in ("description", "enum", "required"):
        if key in schema:
            out[key] = schema[key]
    if "properties" in schema:
        out["properties"] = {k: to_gemini_schema(v) for k, v in schema["properties"].items()}
    if "items" in schema:
        out["items"] = to_gemini_schema(schema["items"])
    return out


class GeminiService(JsonLLMService):
    mode = "gemini"

    def __init__(self, api_key: str, model: str, post: HttpPost = http_post):
        self.api_key = api_key
        self.model = model
        self.label = "Gemini"
        self._post = post

    def _contents(self, messages: list[dict], file: Attachment | None) -> list[dict]:
        contents = []
        for i, m in enumerate(messages):
            parts: list[dict] = []
            if file is not None and i == len(messages) - 1:
                if file.kind in ("pdf", "image"):
                    parts.append({"inline_data": {"mime_type": file.media_type, "data": file.data_b64}})
                else:
                    parts.append({"text": file.as_prompt_text()})
            parts.append({"text": m["content"]})
            contents.append({"role": "model" if m["role"] == "assistant" else "user", "parts": parts})
        return contents

    async def _generate(self, body: dict) -> str:
        url = f"{API_ROOT}/{self.model}:generateContent"
        status, data = await self._post(url, body, {"x-goog-api-key": self.api_key}, 90.0)
        if status != 200:
            raise _error(status, data)
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError):
            reason = (data.get("promptFeedback") or {}).get("blockReason") if isinstance(data, dict) else None
            raise AIError(f"Gemini returned no answer{f' ({reason})' if reason else ''}. Try rephrasing.") from None
        return "".join(p.get("text", "") for p in parts)

    async def _json(self, system, messages, schema, file=None) -> dict:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": self._contents(messages, file),
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": to_gemini_schema(schema),
                "temperature": 0.3,
            },
        }
        return parse_json_text(await self._generate(body))

    async def _text(self, system, messages) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": self._contents(messages, None),
            "generationConfig": {"temperature": 0.6, "maxOutputTokens": 800},
        }
        return await self._generate(body)


def _error(status: int, data: dict) -> AIError:
    message = (data.get("error") or {}).get("message", "") if isinstance(data, dict) else ""
    if status in (400, 403) and "API key" in message:
        return AIError("The Gemini API key is invalid. Check GEMINI_API_KEY in backend/.env.", 500)
    if status == 404:
        return AIError(f"Gemini model not found. Set GEMINI_MODEL in backend/.env. ({message})", 500)
    if status == 429:
        return AIError("Gemini's free-tier limit was reached. Wait a minute (or until tomorrow for the daily limit).", 429)
    if status == 400:
        return AIError(f"Gemini rejected the request: {message}", 400)
    return AIError("Gemini could not be reached. Try again.", 502)
