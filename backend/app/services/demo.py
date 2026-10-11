"""Offline "demo mode" used when no ANTHROPIC_API_KEY is set, so anyone can run the repo.

Planning falls back to the deterministic scheduler. The chatbot uses a simple
keyword heuristic on text files, which doubles as a baseline to compare the
AI's difficulty ratings against.
"""

from __future__ import annotations

import re
from datetime import date

from ..dates import parse_date

HARD_SIGNALS = ["research", "citation", "sources", "peer-reviewed", "proof", "prove", "derive", "implement",
                "algorithm", "analysis", "dataset", "thesis", "literature review", "lab report", "statistical"]
EASY_SIGNALS = ["reflection", "short response", "quiz", "worksheet", "summary", "discussion post", "one page", "1 page"]
COURSE_RE = re.compile(r"\b[A-Z]{2,4}\s?\d{3}\b")


def heuristic_assessment(text: str, today: date) -> dict:
    lower = text.lower()
    words = len(text.split())
    hard = [w for w in HARD_SIGNALS if w in lower]
    easy = [w for w in EASY_SIGNALS if w in lower]
    pages_m = re.search(r"(\d+)\s*(?:-|to)?\s*\d*\s*pages?", lower)
    words_m = re.search(r"(\d[\d,]*)\s*words?", lower)
    pages = int(pages_m.group(1)) if pages_m else 0
    word_req = int(words_m.group(1).replace(",", "")) if words_m else 0

    length = 3 if (pages >= 8 or word_req >= 2500) else 1 if (pages >= 4 or word_req >= 1200) else 0
    score = len(hard) * 2 - len(easy) * 2 + length + (1 if words > 600 else 0)
    difficulty = "hard" if score >= 4 else "medium" if score >= 1 else "easy"
    base = {"easy": 1.5, "medium": 4, "hard": 8}[difficulty]
    hours = min(40.0, max(0.5, base + (pages * 0.75 if pages else word_req / 500)))
    hours = round(hours * 2) / 2

    reasons = []
    if hard:
        reasons.append(f"Mentions {', '.join(hard[:3])}")
    if pages:
        reasons.append(f"About {pages} pages required")
    if word_req:
        reasons.append(f"About {word_req} words required")
    if easy:
        reasons.append(f"Looks like a {easy[0]}")
    if not reasons:
        reasons.append("No strong signals of heavy research or technical work")

    due = None
    m = re.search(r"\b(20\d\d-\d\d-\d\d)\b", text)
    if m and (d := parse_date(m.group(1))) and d >= today:
        due = d.isoformat()

    course_m = COURSE_RE.search(text)
    course = course_m.group(0) if course_m else ""
    first_line = next((ln.strip() for ln in text.splitlines() if len(ln.strip()) > 3), "Uploaded assignment")
    title = re.sub(r"^[\s:–—-]+", "", first_line.replace(course, "")) if course else first_line

    return {
        "reply": f"Demo mode estimate (no API key set): this looks {difficulty}, roughly {hours:g} hours. "
                 "Set up an AI provider in backend/.env for a real read of the assignment.",
        "title": (title or first_line)[:60],
        "course": course,
        "difficulty": difficulty,
        "estimated_hours": hours,
        "due_date": due,
        "reasons": reasons,
        "first_steps": ["Read the full prompt and highlight every requirement", "List the parts and guess a time for each"],
    }


class DemoService:
    mode = "demo"
    model = None
    label = "Demo"

    async def plan(self, assignment, ctx) -> dict:
        raise RuntimeError("demo mode")

    async def rebalance(self, sessions, assignments, ctx) -> dict:
        raise RuntimeError("demo mode")

    async def breakdown(self, session, assignment) -> list[str]:
        work = f"Work {max(10, session.minutes - 10)} minutes on: {session.task}"[:80]
        return ["Gather what you need", work, "Note where to pick up next time"]

    async def assess(self, *, history, file, user_text, today) -> dict:
        if not file.text:
            return {
                "reply": "I'm in demo mode (no API key), so I can only read text files and PDFs with selectable text. "
                         "Set up Gemini, Ollama or Claude in backend/.env to read photos and scans.",
                "difficulty": None,
            }
        return heuristic_assessment(file.text, today)

    async def chat(self, *, history, plan_summary, today) -> str:
        return ("I'm running in demo mode, so I can't chat yet. Set up Gemini (free), Ollama (free, local) or Claude in backend/.env to turn me on."
                f"\n\nYour plan right now:\n{plan_summary or 'No assignments yet.'}")
