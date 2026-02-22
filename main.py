# Copyright (c) 2026 carpaty
# SPDX-License-Identifier: MIT

from __future__ import annotations

import base64
import io
import time
import uuid
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(title="API Emulator", version="0.1.0")

DEFAULT_MODEL = "emulator-llm"
_DUMMY_PNG_BYTES = base64.b64decode(
    "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"
)


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


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/image")
def image() -> StreamingResponse:
    buffer = io.BytesIO(_DUMMY_PNG_BYTES)
    return StreamingResponse(buffer, media_type="image/png")


@app.get("/v1/models")
def openai_models() -> dict[str, Any]:
    created = int(time.time())
    return {
        "object": "list",
        "data": [
            {"id": DEFAULT_MODEL, "object": "model", "created": created, "owned_by": "api-emulator"},
            {"id": "emulator-embedding", "object": "model", "created": created, "owned_by": "api-emulator"},
        ],
    }


@app.post("/v1/chat/completions")
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


@app.post("/v1/completions")
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


@app.post("/v1/embeddings")
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


@app.get("/api/tags")
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


@app.post("/api/generate")
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


@app.post("/api/chat")
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
