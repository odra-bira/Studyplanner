"""Settings from environment variables (and backend/.env)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
log = logging.getLogger("studyease")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    # claude | gemini | ollama | demo. Empty = pick automatically from whichever key is set.
    ai_provider: str = _env("AI_PROVIDER").lower()

    anthropic_api_key: str = _env("ANTHROPIC_API_KEY")
    anthropic_model: str = _env("ANTHROPIC_MODEL", "claude-sonnet-5-5")

    gemini_api_key: str = _env("GEMINI_API_KEY")
    gemini_model: str = _env("GEMINI_MODEL", "gemini-flash-latest")

    ollama_model: str = _env("OLLAMA_MODEL", "gemma3:4b")
    ollama_host: str = _env("OLLAMA_HOST", "http://localhost:11434")

    serve_frontend: bool = _env("SERVE_FRONTEND") == "1"
    cors_origins: tuple[str, ...] = tuple(o for o in _env("CORS_ORIGINS").split(",") if o)

    def provider(self) -> str:
        if self.ai_provider in ("claude", "gemini", "ollama", "demo"):
            return self.ai_provider
        if self.ai_provider:
            log.warning("Unknown AI_PROVIDER=%r, picking automatically.", self.ai_provider)
        if self.anthropic_api_key:
            return "claude"
        if self.gemini_api_key:
            return "gemini"
        return "demo"


def build_ai(settings: Settings):
    """Create the AI service named by AI_PROVIDER (or the first one with a key)."""
    provider = settings.provider()

    if provider == "claude":
        if not settings.anthropic_api_key:
            log.warning("AI_PROVIDER=claude but ANTHROPIC_API_KEY is empty; using demo mode.")
        else:
            from .services.claude import ClaudeService

            return ClaudeService(settings.anthropic_api_key, settings.anthropic_model)

    if provider == "gemini":
        if not settings.gemini_api_key:
            log.warning("AI_PROVIDER=gemini but GEMINI_API_KEY is empty; using demo mode.")
        else:
            from .services.gemini import GeminiService

            return GeminiService(settings.gemini_api_key, settings.gemini_model)

    if provider == "ollama":
        from .services.ollama import OllamaService

        return OllamaService(settings.ollama_model, settings.ollama_host)

    from .services.demo import DemoService

    return DemoService()
