# Copyright (c) 2026 carpaty
# SPDX-License-Identifier: MIT

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="API Emulator", version="0.1.0")

DEFAULT_MODEL = "emulator-llm"


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
