from pathlib import Path
import sys

from fastapi.testclient import TestClient

# Ensure local module imports work in CI regardless of runner cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
from main import app


client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pinggy_set_and_get_location_header():
    main._pinggy_url_fallback = None

    set_response = client.post("/pinggy", json={"URL": "https://some.com"})
    assert set_response.status_code == 200
    assert set_response.json() == {"URL": "https://some.com"}

    get_response = client.get("/pinggy", follow_redirects=False)
    assert get_response.status_code == 307
    assert get_response.headers["location"] == "https://some.com"


def test_openai_chat_includes_user_request():
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello emulator"}],
        "stream": False,
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "choices" in body
    assert "user_request" in body
    assert body["user_request"]["messages"][0]["content"] == "Hello emulator"


def test_ollama_generate_includes_user_request():
    payload = {"model": "llama3", "prompt": "Say hi", "stream": False}
    response = client.post("/api/generate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "response" in body
    assert body["user_request"]["prompt"] == "Say hi"
