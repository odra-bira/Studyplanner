"""FastAPI app: routes, uploads, error handling.

Run:  uvicorn app.main:app --reload --port 3001   (from the backend folder)
Docs: http://localhost:3001/docs
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .config import Settings, build_ai
from .files import MAX_UPLOAD_BYTES, Upload, UploadError
from .planner import BadRequest, Planner
from .schemas import (
    BreakdownRequest, BreakdownResponse, ChatPayload, ChatResponse, Health,
    PlanRequest, PlanResponse, RebalanceRequest, RebalanceResponse,
)
from .services.base import AIError

logging.basicConfig(level=logging.INFO)
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "client" / "dist"


def _first_error(err: ValidationError | RequestValidationError) -> str:
    """Turn Pydantic's error list into one readable sentence for the UI."""
    e = err.errors()[0]
    field = ".".join(str(p) for p in e.get("loc", []) if p not in ("body",))
    return f"{field}: {e.get('msg')}" if field else str(e.get("msg"))


def create_app(planner: Planner | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    planner = planner or Planner(build_ai(settings))
    app = FastAPI(title="StudyEase API", version="1.0.0", description="Study planning with Claude.")

    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"])

    # ---------- errors: always {"error": "..."} so the client can show it ----------

    @app.exception_handler(RequestValidationError)
    async def on_validation(_req: Request, err: RequestValidationError):
        return JSONResponse({"error": _first_error(err)}, status_code=400)

    @app.exception_handler(BadRequest)
    @app.exception_handler(UploadError)
    async def on_bad_request(_req: Request, err: Exception):
        return JSONResponse({"error": str(err)}, status_code=400)

    @app.exception_handler(AIError)
    async def on_ai_error(_req: Request, err: AIError):
        return JSONResponse({"error": str(err)}, status_code=err.status)

    # ---------- routes ----------

    @app.get("/api/health", response_model=Health)
    async def health():
        return planner.health()

    @app.post("/api/plan", response_model=PlanResponse)
    async def plan(req: PlanRequest):
        return await planner.plan(req)

    @app.post("/api/rebalance", response_model=RebalanceResponse)
    async def rebalance(req: RebalanceRequest):
        return await planner.rebalance(req)

    @app.post("/api/breakdown", response_model=BreakdownResponse)
    async def breakdown(req: BreakdownRequest):
        return await planner.breakdown(req)

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(payload: str = Form(...), file: UploadFile | None = File(None)):
        try:
            data = ChatPayload.model_validate(json.loads(payload))
        except (json.JSONDecodeError, ValidationError) as err:
            raise BadRequest(_first_error(err) if isinstance(err, ValidationError) else "Invalid chat payload.") from err
        upload = None
        if file is not None and file.filename:
            raw = await file.read(MAX_UPLOAD_BYTES + 1)
            upload = Upload(raw, file.content_type or "", file.filename)
        return await planner.chat(data, upload)

    # ---------- production: serve the built React app ----------

    if settings.serve_frontend and FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            target = (FRONTEND_DIST / path).resolve()
            inside = target.is_relative_to(FRONTEND_DIST.resolve())
            return FileResponse(target if path and inside and target.is_file() else FRONTEND_DIST / "index.html")

    return app


app = create_app()
