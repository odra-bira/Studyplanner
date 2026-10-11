# StudyEase — Adaptive Study Planner

**Odra Bira** · FastAPI · React · Python · Pydantic · LLM integrations

StudyEase is a workload-aware study planner that turns assignments and due dates into manageable study sessions. It estimates difficulty, considers available time, and offers a structured weekly plan.

## Features

- Assignment scheduling based on time availability, workload, and deadlines
- Structured, LLM-assisted planning with validation and schedule repair
- Assignment file upload with estimated difficulty and suggested next steps
- Rebalance missed or overloaded study sessions
- Task breakdown into actionable steps
- Optional stress check-in and break timer
- Demo mode without external AI credentials
- Provider adapters for Gemini, Ollama, and Claude APIs

**Provider integrations are software dependencies, not project contributors.**

## Project architecture

```text
React frontend (Vite)
     |
     v
FastAPI backend (Pydantic)
     |-- Assignment and planning endpoints
     |-- LLM provider adapters
     |-- Deterministic scheduling and repair
     +-- File parsing and validation
```

## Run locally

```bash
npm install
npm install --prefix client
python -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
npm run dev
```

See `backend/.env.example` for optional provider settings. Without API keys, demo mode provides basic planning features. Never commit your `.env` file or API keys.

## Tests

```bash
cd backend
python -m pytest
```

## Repository notes

The source archive contains a React client, FastAPI backend, provider adapters, scheduling logic and tests. The complete cleaned source archive has been prepared separately for import; this README is the initial public entry point.

## Author

**Odra Bira** · [Portfolio](https://odra-bira.github.io/) · [GitHub](https://github.com/odra-bira)
