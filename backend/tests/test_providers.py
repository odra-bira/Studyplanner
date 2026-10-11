"""Gemini and Ollama services, tested with a fake HTTP layer (no network, no keys)."""

import asyncio
import json
from datetime import date

import pytest

from app.config import Settings, build_ai
from app.files import Upload, to_attachment
from app.scheduler import PlanContext
from app.schemas import Assignment
from app.services.base import AIError, parse_json_text
from app.services.gemini import GeminiService, to_gemini_schema
from app.services.ollama import OllamaService, simplify_schema

ASSIGNMENT = Assignment.model_validate({"title": "Essay", "due": "2026-10-16", "difficulty": "medium", "hours": 3})
CTX = PlanContext(today=date(2026, 10, 12), daily=60)
PLAN = {"sessions": [{"date": "2026-10-13", "minutes": 60, "task": "Outline", "why": "early"}], "note": "ok"}


class FakePost:
    """Records the request and returns a canned (status, body)."""

    def __init__(self, status, body):
        self.status, self.body, self.calls = status, body, []

    async def __call__(self, url, body, headers, timeout):
        self.calls.append({"url": url, "body": body, "headers": headers})
        return self.status, self.body


def run(coro):
    return asyncio.run(coro)


def gemini_reply(obj):
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(obj)}]}}]}


# ---------- Gemini ----------


def test_gemini_plan_sends_schema_and_parses_json():
    post = FakePost(200, gemini_reply(PLAN))
    out = run(GeminiService("key", "gemini-flash-latest", post).plan(ASSIGNMENT, CTX))
    assert out["sessions"][0]["task"] == "Outline"
    call = post.calls[0]
    assert call["url"].endswith("/gemini-flash-latest:generateContent")
    assert call["headers"]["x-goog-api-key"] == "key"
    config = call["body"]["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert config["responseSchema"]["type"] == "OBJECT"


def test_gemini_sends_pdf_inline():
    post = FakePost(200, gemini_reply({"reply": "Hard.", "difficulty": "hard"}))
    pdf = to_attachment(Upload(b"%PDF-1.4 not really", "application/pdf", "a.pdf"))
    run(GeminiService("key", "m", post).assess(history=[], file=pdf, user_text="", today=CTX.today))
    parts = post.calls[0]["body"]["contents"][-1]["parts"]
    assert parts[0]["inline_data"]["mime_type"] == "application/pdf"


def test_gemini_rate_limit_message():
    post = FakePost(429, {"error": {"message": "quota"}})
    with pytest.raises(AIError) as err:
        run(GeminiService("key", "m", post).plan(ASSIGNMENT, CTX))
    assert err.value.status == 429


def test_gemini_schema_conversion_handles_nullable():
    s = to_gemini_schema({"type": "object", "properties": {"due": {"type": ["string", "null"]}}, "required": ["due"]})
    assert s["properties"]["due"] == {"type": "STRING", "nullable": True}
    assert s["required"] == ["due"]


# ---------- Ollama ----------


def test_ollama_plan_uses_format_schema():
    post = FakePost(200, {"message": {"content": json.dumps(PLAN)}})
    out = run(OllamaService("gemma3:4b", post=post).plan(ASSIGNMENT, CTX))
    assert out["note"] == "ok"
    body = post.calls[0]["body"]
    assert post.calls[0]["url"] == "http://localhost:11434/api/chat"
    assert body["format"]["type"] == "object"
    assert body["stream"] is False
    assert body["messages"][0]["role"] == "system"


def test_ollama_sends_images_and_text():
    post = FakePost(200, {"message": {"content": json.dumps({"reply": "ok", "difficulty": "easy"})}})
    svc = OllamaService("gemma3:4b", post=post)
    img = to_attachment(Upload(b"\x89PNG...", "image/png", "a.png"))
    run(svc.assess(history=[], file=img, user_text="", today=CTX.today))
    assert post.calls[-1]["body"]["messages"][-1]["images"]
    txt = to_attachment(Upload(b"Write a 5 page essay.", "text/plain", "a.txt"))
    run(svc.assess(history=[], file=txt, user_text="", today=CTX.today))
    assert "5 page essay" in post.calls[-1]["body"]["messages"][-1]["content"]


def test_ollama_scanned_pdf_gives_clear_error():
    svc = OllamaService("gemma3:4b", post=FakePost(200, {}))
    pdf = to_attachment(Upload(b"%PDF-1.4 not really", "application/pdf", "scan.pdf"))  # no extractable text
    with pytest.raises(AIError):
        run(svc.assess(history=[], file=pdf, user_text="", today=CTX.today))


def test_ollama_missing_model_message():
    post = FakePost(404, {"error": "model 'gemma3:4b' not found"})
    with pytest.raises(AIError) as err:
        run(OllamaService("gemma3:4b", post=post).plan(ASSIGNMENT, CTX))
    assert "ollama pull" in str(err.value)


def test_simplify_schema_drops_null_union():
    assert simplify_schema({"type": ["string", "null"]}) == {"type": "string"}


# ---------- shared ----------


def test_parse_json_text_tolerates_fences_and_chatter():
    assert parse_json_text('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_text('Sure! {"a": 2} Hope that helps.') == {"a": 2}
    with pytest.raises(AIError):
        parse_json_text("no json here")


def test_provider_selection():
    assert build_ai(Settings(ai_provider="", anthropic_api_key="", gemini_api_key="")).mode == "demo"
    assert build_ai(Settings(ai_provider="", anthropic_api_key="", gemini_api_key="g")).mode == "gemini"
    assert build_ai(Settings(ai_provider="ollama", anthropic_api_key="", gemini_api_key="")).mode == "ollama"
    assert build_ai(Settings(ai_provider="gemini", anthropic_api_key="", gemini_api_key="")).mode == "demo"  # no key
