# StudyEase

A difficulty- and workload-aware study planner for college students.

Deadlines tell students when work is due. They don't say what to do today. You add an assignment and StudyEase splits it into dated study sessions that fit your daily free time, with a short reason for each one. Upload an assignment sheet to the chatbot and an LLM rates the difficulty and estimates the hours.

**Stack:** Python · FastAPI · Pydantic · LLM APIs (Claude, Gemini, local models via Ollama) · React 18 (Vite) · pytest

## Features

- **Three AI providers, one switch.** Google Gemini (free tier), a local open-source model through Ollama (free, offline), or Anthropic Claude, chosen with `AI_PROVIDER` in `.env`.
- **LLM study plans.** The model drafts sessions from the assignment, due date, difficulty, your time estimate, the time you have free each day, and what's already booked.
- **Output checking and repair.** LLM output is never trusted as-is. A deterministic scheduler pulls dates into the allowed window, rescales totals to your estimate, and moves sessions off days that are already full. See `backend/app/scheduler.py`.
- **Assignment chatbot with difficulty rating.** Upload a PDF, photo or text file. The model reads it (multimodal input) and returns a structured rating (easy, medium or hard), an hour estimate, the due date if it finds one, the reasons for its rating, and first steps. One click adds it to your plan.
- **Rebalance my week.** Moves missed and overloaded sessions. Model-proposed moves are accepted only if they stay before the due date and keep each assignment's steps in order.
- **Break down.** Turns one session into a 3–5 step checklist.
- **Optional stress check-in.** When it's set to high, new plans use shorter sessions. It makes no health claims.
- **Demo mode.** With no provider set up, the app still runs. It uses a built-in planner and a keyword-based difficulty baseline for text files and text PDFs.

## How it works

```
React client ──fetch──▶ FastAPI (Pydantic validation)
                            │
                            ├──▶ Planner (business logic)
                            │       ├──▶ AI service ── Claude (forced tool use) / Gemini (responseSchema)
                            │       │                  / Ollama (format) ──▶ JSON matching a schema
                            │       └──▶ scheduler.py  ── validate + repair, or plan offline
                            └──▶ /docs (auto-generated OpenAPI)
```

Design choices:

- **Structured LLM output.** Every AI feature except free chat defines its JSON shape once (`backend/app/prompts.py`). Each provider enforces it its own way: Claude with forced tool use, Gemini with `responseSchema`, Ollama with `format`.
- **Guardrails after the model.** `normalize_plan` and `apply_moves` treat model output as untrusted input. The model suggests, and the code enforces the rules.
- **Graceful fallback.** If the API call fails or returns nothing usable, the deterministic planner takes over and the response says which one answered (`source: "ai" | "local"`).
- **Swappable AI layer.** All providers share one interface (`services/base.py`), and Gemini and Ollama share one base class. HTTP goes through a single injectable function, so tests use a fake and need no network or API key.
- **Typed API.** Pydantic models validate every request. FastAPI turns them into interactive docs at `/docs`.

## Run it locally

You need Python 3.10+ and Node 18+.

```bash
# 1. Backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then pick a provider (below), or leave it for demo mode
cd ..

# 2. Frontend
npm run setup:web

# 3. Run both (with the virtualenv still active)
npm run dev                        # API on :3001, web app on http://localhost:5173
```

API docs: http://localhost:3001/docs

### Choosing an AI provider

Edit `backend/.env`, then restart `npm run dev`. The pill at the top of the app shows which one is active.

| Provider | Cost | Setup in `backend/.env` |
|---|---|---|
| **Gemini** | Free tier (daily limits) | Get a key at https://aistudio.google.com/apikey, then set `AI_PROVIDER=gemini` and `GEMINI_API_KEY=...` |
| **Ollama** | Free, runs locally | Install https://ollama.com, run `ollama pull gemma3:4b`, then set `AI_PROVIDER=ollama` |
| **Claude** | Pay-as-you-go | Get a key at https://console.anthropic.com, then set `AI_PROVIDER=claude` and `ANTHROPIC_API_KEY=...` |

Notes:
- On Gemini's free tier, Google may use prompts to improve its products, so test with sample assignments rather than personal files.
- Ollama gets text extracted from PDFs. Photos need a vision model such as `gemma3:4b`. Scanned PDFs without text won't work there, so upload a photo instead.

```bash
npm test                           # pytest: scheduler, planner logic, HTTP endpoints
```

**Single-server deploy:** run `npm run build`, set `SERVE_FRONTEND=1` and start `uvicorn app.main:app --host 0.0.0.0 --port 3001` from `backend/`. FastAPI then serves the API and the built React app.

## Project structure

```
backend/
  app/
    main.py               FastAPI app: routes, uploads, error handlers
    planner.py            business logic behind each endpoint
    scheduler.py          normalize_plan, local_plan, local_rebalance, apply_moves
    schemas.py            Pydantic request/response models (camelCase JSON)
    prompts.py            prompts + tool schemas for structured output
    files.py              uploads → provider-neutral attachment (+ PDF text extraction)
    config.py             env settings, picks the AI provider
    services/
      base.py             AIService interface, shared JSON-mode base, HTTP helper
      claude.py           Anthropic SDK (async)
      gemini.py           Gemini REST API
      ollama.py           local models via Ollama
      demo.py             offline fallback + keyword difficulty baseline
  tests/                  pytest
client/
  src/
    App.jsx               layout and API calls
    hooks/usePlanner.js   reducer + localStorage persistence
    components/           AssignmentForm, PlanView, SessionCard, Sidebar, ChatBot
```

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | – | `{ ai: "claude" \| "demo", model }` |
| POST | `/api/plan` | `{ today, daily, mood, assignment, sessions }` | `{ source, note, warnings, sessions }` |
| POST | `/api/rebalance` | `{ today, daily, mood, assignments, sessions }` | `{ source, note, moves }` |
| POST | `/api/breakdown` | `{ session, assignment }` | `{ steps }` |
| POST | `/api/chat` | multipart: `payload` (JSON) + optional `file` | `{ reply, assessment }` |

## Roadmap

- **Evaluate the difficulty ratings.** Collect assignment sheets with students' own difficulty ratings and the hours they actually spent. Measure the LLM's agreement with them and its hour error against the keyword baseline.
- **Train a small model.** Fit a scikit-learn regressor on text features to predict hours, and compare it with the LLM on cost, speed and accuracy.
- **Accounts and a database** (e.g. PostgreSQL) so plans sync across devices. Plans currently save in the browser.
- **Usability study** with 4–5 students (Nov 2–15). Record task success and points of confusion.

## Background

Built for a design-track course project at the University at Buffalo. The interface follows the concept from the midterm deck: assignment input, suggested sessions with reasons, easy editing, and an optional stress check-in.

## License

Copyright (c) 2026 odra-bira. All rights reserved. This code is public for viewing only; see [LICENSE](LICENSE). Please do not copy or reuse it without permission.
