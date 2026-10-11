"""HTTP-level tests through FastAPI's TestClient (demo mode, no network)."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.planner import Planner  # noqa: E402
from app.services.demo import DemoService  # noqa: E402

client = TestClient(create_app(Planner(DemoService()), Settings(anthropic_api_key="")))
BASE = {"today": "2026-10-12", "daily": 60}
ASSIGNMENT = {"id": "a1", "title": "Lab report", "due": "2026-10-16", "difficulty": "hard", "hours": 3}


def test_health():
    assert client.get("/api/health").json()["ai"] == "demo"


def test_plan_returns_camel_case_sessions():
    res = client.post("/api/plan", json={**BASE, "assignment": ASSIGNMENT, "sessions": []})
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "local"
    assert body["sessions"][-1]["date"] == "2026-10-16"


def test_validation_errors_use_error_key():
    res = client.post("/api/plan", json={**BASE, "assignment": {**ASSIGNMENT, "hours": -1}})
    assert res.status_code == 400
    assert "hours" in res.json()["error"]


def test_chat_upload():
    files = {"file": ("lab.txt", b"Write a 10 page lab report with peer-reviewed sources.", "text/plain")}
    res = client.post("/api/chat", data={"payload": '{"today": "2026-10-12"}'}, files=files)
    assert res.status_code == 200
    assert res.json()["assessment"]["difficulty"] == "hard"


def test_chat_bad_file_is_400():
    files = {"file": ("a.zip", b"PK..", "application/zip")}
    res = client.post("/api/chat", data={"payload": '{"today": "2026-10-12"}'}, files=files)
    assert res.status_code == 400
