"""A free, local open-source model through Ollama (https://ollama.com).

Install Ollama, run `ollama pull gemma3:4b`, then set AI_PROVIDER=ollama.
Nothing leaves your computer. The `format` field constrains the reply to our
JSON Schema. PDFs are sent as extracted text; photos need a vision model.
"""

from __future__ import annotations

from ..files import Attachment
from .base import AIError, HttpPost, JsonLLMService, http_post, parse_json_text


def simplify_schema(schema: dict) -> dict:
    """Ollama's grammar handles plain types best: turn ["string", "null"] into "string"."""
    out = dict(schema)
    if isinstance(out.get("type"), list):
        out["type"] = next((t for t in out["type"] if t != "null"), "string")
    if "properties" in out:
        out["properties"] = {k: simplify_schema(v) for k, v in out["properties"].items()}
    if "items" in out:
        out["items"] = simplify_schema(out["items"])
    return out


class OllamaService(JsonLLMService):
    mode = "ollama"

    def __init__(self, model: str, host: str = "http://localhost:11434", post: HttpPost = http_post):
        self.model = model
        self.host = host.rstrip("/")
        self.label = f"Ollama ({model})"
        self._post = post

    def _messages(self, system: str, messages: list[dict], file: Attachment | None) -> list[dict]:
        out = [{"role": "system", "content": system}]
        for i, m in enumerate(messages):
            msg = {"role": m["role"], "content": m["content"]}
            if file is not None and i == len(messages) - 1:
                if file.kind == "image":
                    msg["images"] = [file.data_b64]
                elif file.text:
                    msg["content"] = f"{file.as_prompt_text()}\n\n{m['content']}"
                else:
                    raise AIError("This PDF has no readable text (it may be a scan). Upload a photo of it or a text file instead.", 400)
            out.append(msg)
        return out

    async def _chat(self, body: dict) -> str:
        status, data = await self._post(f"{self.host}/api/chat", body, {}, 180.0)
        if status != 200:
            message = data.get("error", "") if isinstance(data, dict) else ""
            if status == 404 or "not found" in message:
                raise AIError(f"Ollama model '{self.model}' isn't downloaded. Run: ollama pull {self.model}", 500)
            if "image" in message.lower() or "vision" in message.lower():
                raise AIError(f"'{self.model}' can't read images. Use a vision model such as gemma3:4b, or upload a PDF.", 400)
            raise AIError(f"Ollama error: {message or status}", 502)
        return (data.get("message") or {}).get("content", "")

    async def _json(self, system, messages, schema, file=None) -> dict:
        body = {
            "model": self.model,
            "messages": self._messages(system, messages, file),
            "format": simplify_schema(schema),
            "stream": False,
            "options": {"temperature": 0.2},
        }
        return parse_json_text(await self._chat(body))

    async def _text(self, system, messages) -> str:
        body = {"model": self.model, "messages": self._messages(system, messages, None), "stream": False}
        return await self._chat(body)
