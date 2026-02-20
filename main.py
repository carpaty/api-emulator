# Copyright (c) 2026 carpaty
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

asgi_app = FastAPI(title="API Emulator", version="0.1.0")

DEFAULT_MODEL = "emulator-llm"
PINGGY_CACHE_KEY = "pinggy_url"
_pinggy_url_fallback: str | None = None
_IS_GAE_STD = os.getenv("GAE_ENV", "").startswith("standard")
_logger = logging.getLogger(__name__)
_memcache_import_error: Exception | None = None

try:
    from google.appengine.api import memcache as gae_memcache
except Exception as exc:  # pragma: no cover - depends on runtime environment
    gae_memcache = None
    _memcache_import_error = exc
    if _IS_GAE_STD:
        _logger.exception("App Engine memcache import failed")


class OpenAIMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]] | None = None


class OpenAIChatRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: list[OpenAIMessage] = Field(default_factory=list)
    stream: bool = False


class OpenAICompletionRequest(BaseModel):
    model: str = DEFAULT_MODEL
    prompt: str | list[str]
    stream: bool = False


class OpenAIEmbeddingRequest(BaseModel):
    model: str = "emulator-embedding"
    input: str | list[str]


class OllamaGenerateRequest(BaseModel):
    model: str = DEFAULT_MODEL
    prompt: str = ""
    stream: bool = False


class OllamaChatRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: list[dict[str, Any]] = Field(default_factory=list)
    stream: bool = False


class PinggyRequest(BaseModel):
    URL: str


def _extract_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _fake_text(seed: str) -> str:
    cleaned = seed.strip() or "empty prompt"
    return f"Fake response from emulator. User request: {cleaned[:300]}"


def _memcache_client() -> Any | None:
    if gae_memcache is None:
        return None

    try:
        # Build client inside request context to get active security ticket.
        return gae_memcache.Client()
    except Exception as exc:
        if _IS_GAE_STD:
            raise HTTPException(status_code=500, detail=f"Memcache client exception: {exc}")
        return None


def _pinggy_set(url: str) -> None:
    global _pinggy_url_fallback

    client = _memcache_client()
    if client is not None:
        try:
            ok = client.set(PINGGY_CACHE_KEY, url)
            if ok:
                return
            if _IS_GAE_STD:
                raise HTTPException(status_code=500, detail="Memcache set failed")
        except HTTPException:
            raise
        except Exception as exc:
            if _IS_GAE_STD:
                raise HTTPException(status_code=500, detail=f"Memcache set exception: {exc}")

    if _IS_GAE_STD:
        detail = "Memcache unavailable"
        if _memcache_import_error is not None:
            detail = f"Memcache unavailable: {_memcache_import_error}"
        raise HTTPException(status_code=500, detail=detail)

    _pinggy_url_fallback = url


def _pinggy_get() -> str | None:
    client = _memcache_client()
    if client is not None:
        try:
            cached = client.get(PINGGY_CACHE_KEY)
            if isinstance(cached, str) and cached:
                return cached
        except Exception as exc:
            if _IS_GAE_STD:
                raise HTTPException(status_code=500, detail=f"Memcache get exception: {exc}")

    if _IS_GAE_STD and _memcache_import_error is not None:
        raise HTTPException(status_code=500, detail=f"Memcache unavailable: {_memcache_import_error}")

    return _pinggy_url_fallback


@asgi_app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@asgi_app.post("/pinggy")
async def pinggy_set(req: PinggyRequest) -> dict[str, str]:
    _pinggy_set(req.URL)
    return {"URL": req.URL}


@asgi_app.get("/pinggy")
async def pinggy_get() -> Response:
    url = _pinggy_get()
    if not url:
        raise HTTPException(status_code=404, detail="Pinggy URL not set")
    return Response(status_code=307, headers={"Location": url})


@asgi_app.get("/v1/models")
def openai_models() -> dict[str, Any]:
    created = int(time.time())
    return {
        "object": "list",
        "data": [
            {"id": DEFAULT_MODEL, "object": "model", "created": created, "owned_by": "api-emulator"},
            {"id": "emulator-embedding", "object": "model", "created": created, "owned_by": "api-emulator"},
        ],
    }


@asgi_app.post("/v1/chat/completions")
def openai_chat(req: OpenAIChatRequest) -> dict[str, Any]:
    last_msg = req.messages[-1].content if req.messages else ""
    content = _fake_text(_extract_text(last_msg))
    now = int(time.time())
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": now,
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 18, "total_tokens": 30},
        "user_request": {"model": req.model, "messages": [m.model_dump() for m in req.messages], "stream": req.stream},
    }


@asgi_app.post("/v1/completions")
def openai_completions(req: OpenAICompletionRequest) -> dict[str, Any]:
    prompt = _extract_text(req.prompt)
    text = _fake_text(prompt)
    now = int(time.time())
    return {
        "id": f"cmpl-{uuid.uuid4().hex[:24]}",
        "object": "text_completion",
        "created": now,
        "model": req.model,
        "choices": [{"text": text, "index": 0, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 14, "total_tokens": 22},
        "user_request": {"model": req.model, "prompt": req.prompt, "stream": req.stream},
    }


@asgi_app.post("/v1/embeddings")
def openai_embeddings(req: OpenAIEmbeddingRequest) -> dict[str, Any]:
    inputs = req.input if isinstance(req.input, list) else [req.input]
    data = []
    for i, item in enumerate(inputs):
        text = _extract_text(item)
        base = float((len(text) % 10) + 1)
        vector = [base, base + 0.1, base + 0.2, base + 0.3]
        data.append({"object": "embedding", "index": i, "embedding": vector})

    return {
        "object": "list",
        "data": data,
        "model": req.model,
        "usage": {"prompt_tokens": len(inputs) * 5, "total_tokens": len(inputs) * 5},
        "user_request": {"model": req.model, "input": req.input},
    }


@asgi_app.get("/api/tags")
def ollama_tags() -> dict[str, Any]:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "models": [
            {
                "name": f"{DEFAULT_MODEL}:latest",
                "model": f"{DEFAULT_MODEL}:latest",
                "modified_at": now,
                "size": 123456789,
                "digest": "sha256:apiemulator",
                "details": {"format": "gguf", "family": "emulator", "parameter_size": "1B", "quantization_level": "Q4_0"},
            }
        ]
    }


@asgi_app.post("/api/generate")
def ollama_generate(req: OllamaGenerateRequest) -> dict[str, Any]:
    response_text = _fake_text(req.prompt)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "model": req.model,
        "created_at": now,
        "response": response_text,
        "done": True,
        "done_reason": "stop",
        "context": [1, 2, 3, 4],
        "total_duration": 1000000,
        "load_duration": 10000,
        "prompt_eval_count": 8,
        "prompt_eval_duration": 200000,
        "eval_count": 12,
        "eval_duration": 500000,
        "user_request": {"model": req.model, "prompt": req.prompt, "stream": req.stream},
    }


@asgi_app.post("/api/chat")
def ollama_chat(req: OllamaChatRequest) -> dict[str, Any]:
    content = ""
    if req.messages:
        content = _extract_text(req.messages[-1].get("content"))

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "model": req.model,
        "created_at": now,
        "message": {"role": "assistant", "content": _fake_text(content)},
        "done": True,
        "done_reason": "stop",
        "total_duration": 900000,
        "load_duration": 9000,
        "prompt_eval_count": 8,
        "prompt_eval_duration": 180000,
        "eval_count": 10,
        "eval_duration": 400000,
        "user_request": {"model": req.model, "messages": req.messages, "stream": req.stream},
    }


def _wsgi_json_response(start_response: Any, status: str, body: dict[str, Any], headers: list[tuple[str, str]] | None = None) -> list[bytes]:
    payload = json.dumps(body).encode("utf-8")
    final_headers = [("Content-Type", "application/json"), ("Content-Length", str(len(payload)))]
    if headers:
        final_headers.extend(headers)
    start_response(status, final_headers)
    return [payload]


def _wsgi_pinggy_router(asgi_wsgi_app: Any, environ: dict[str, Any], start_response: Any) -> list[bytes]:
    path = environ.get("PATH_INFO", "")
    method = (environ.get("REQUEST_METHOD") or "").upper()
    if path != "/pinggy":
        return asgi_wsgi_app(environ, start_response)

    if method == "POST":
        try:
            content_length = int(environ.get("CONTENT_LENGTH") or "0")
        except ValueError:
            content_length = 0

        raw_body = environ["wsgi.input"].read(content_length) if content_length > 0 else b""
        try:
            payload = json.loads(raw_body.decode("utf-8") if raw_body else "{}")
        except Exception:
            return _wsgi_json_response(start_response, "400 Bad Request", {"detail": "Invalid JSON body"})

        url = payload.get("URL") if isinstance(payload, dict) else None
        if not isinstance(url, str) or not url:
            return _wsgi_json_response(start_response, "422 Unprocessable Entity", {"detail": "URL is required"})

        try:
            _pinggy_set(url)
        except HTTPException as exc:
            return _wsgi_json_response(start_response, f"{exc.status_code} Error", {"detail": exc.detail})

        return _wsgi_json_response(start_response, "200 OK", {"URL": url})

    if method == "GET":
        try:
            url = _pinggy_get()
        except HTTPException as exc:
            return _wsgi_json_response(start_response, f"{exc.status_code} Error", {"detail": exc.detail})

        if not url:
            return _wsgi_json_response(start_response, "404 Not Found", {"detail": "Pinggy URL not set"})

        start_response("307 Temporary Redirect", [("Location", url), ("Content-Length", "0")])
        return [b""]

    start_response("405 Method Not Allowed", [("Allow", "GET, POST"), ("Content-Length", "0")])
    return [b""]


def _build_serving_app() -> Any:
    if not _IS_GAE_STD:
        return asgi_app

    try:
        from a2wsgi import ASGIMiddleware
        from google.appengine.api import wrap_wsgi_app

        asgi_wsgi_app = ASGIMiddleware(asgi_app)

        def _root_wsgi_app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
            return _wsgi_pinggy_router(asgi_wsgi_app, environ, start_response)

        return wrap_wsgi_app(_root_wsgi_app)
    except Exception as exc:
        _logger.exception("Failed to wrap FastAPI app for App Engine bundled APIs: %s", exc)
        return asgi_app


app = _build_serving_app()
