import asyncio
import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from openai import AsyncOpenAI

from app.core.errors import (
    LLMContentBlockedError,
    LLMEmptyResponseError,
    LLMError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.openai_provider import OpenAIProvider
from tests.conftest import make_settings


def _completion(content: str | None, finish_reason: str = "stop") -> dict[str, Any]:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-test",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": content},
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }


def _provider(handler: Callable[[httpx.Request], httpx.Response]) -> OpenAIProvider:
    provider = OpenAIProvider(make_settings(llm_max_retries=0))
    provider._client = AsyncOpenAI(
        api_key="sk-test",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return provider


def _run(provider: OpenAIProvider, query: str = "hello") -> Any:
    return asyncio.run(provider.complete(query))


def test_success_returns_answer_and_usage():
    result = _run(_provider(lambda _: httpx.Response(200, json=_completion("  Hi!  "))))

    assert result.answer == "Hi!"
    assert result.model == "gpt-test"
    assert result.truncated is False
    assert result.usage.total_tokens == 8


def test_length_finish_reason_marks_truncated():
    result = _run(_provider(lambda _: httpx.Response(200, json=_completion("Partial", "length"))))

    assert result.truncated is True


def test_sends_system_prompt_and_user_query():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json=_completion("ok"))

    _run(_provider(handler), "What is JWT?")

    roles = [m["role"] for m in captured["messages"]]
    assert roles == ["system", "user"]
    assert captured["messages"][1]["content"] == "What is JWT?"
    assert captured["max_completion_tokens"] == 800


def _raise_timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("timed out", request=request)


@pytest.mark.parametrize(
    ("handler", "expected"),
    [
        (_raise_timeout, LLMTimeoutError),
        (
            lambda _: httpx.Response(429, json={"error": {"code": "rate_limit"}}),
            LLMUnavailableError,
        ),
        (lambda _: httpx.Response(500, json={"error": {}}), LLMUnavailableError),
        (lambda _: httpx.Response(401, json={"error": {"code": "invalid_api_key"}}), LLMError),
        (
            lambda _: httpx.Response(400, json={"error": {"code": "content_filter"}}),
            LLMContentBlockedError,
        ),
        (lambda _: httpx.Response(200, json=_completion(None)), LLMEmptyResponseError),
        (
            lambda _: httpx.Response(200, json=_completion("", "content_filter")),
            LLMContentBlockedError,
        ),
    ],
    ids=[
        "timeout",
        "rate-limit",
        "server-error",
        "bad-key",
        "content-filter-400",
        "empty",
        "filtered",
    ],
)
def test_failures_map_to_domain_errors(handler, expected):
    with pytest.raises(expected):
        _run(_provider(handler))
