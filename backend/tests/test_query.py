import pytest

from app.core.errors import (
    LLMContentBlockedError,
    LLMEmptyResponseError,
    LLMError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.schemas import MAX_QUERY_LENGTH


def test_health_is_public(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_query_success(client, auth_headers, fake_llm):
    response = client.post(
        "/api/query", json={"query": "  What is the capital of France?  "}, headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Paris is the capital of France."
    assert body["model"] == "fake-model"
    assert body["truncated"] is False
    assert body["usage"]["total_tokens"] == 17
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert fake_llm.calls == ["What is the capital of France?"]


def test_well_formed_request_id_is_propagated(client):
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})

    assert response.headers["X-Request-ID"] == "abc-123"


def test_malformed_request_id_is_replaced(client):
    response = client.get("/health", headers={"X-Request-ID": "bad id\nwith newline"})

    assert response.headers["X-Request-ID"] != "bad id\nwith newline"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"query": ""},
        {"query": "   "},
        {"query": 123},
        {"query": "x" * (MAX_QUERY_LENGTH + 1)},
        {"query": "hi", "unexpected": "field"},
    ],
    ids=["missing", "empty", "whitespace", "wrong-type", "too-long", "extra-field"],
)
def test_invalid_input_returns_400(client, auth_headers, fake_llm, payload):
    response = client.post("/api/query", json=payload, headers=auth_headers)

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_REQUEST"
    assert error["details"]
    assert fake_llm.calls == []


def test_malformed_json_returns_400(client, auth_headers):
    response = client.post(
        "/api/query",
        content=b"{not json",
        headers={**auth_headers, "Content-Type": "application/json"},
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (LLMTimeoutError(), 504, "LLM_TIMEOUT"),
        (LLMUnavailableError(), 503, "LLM_UNAVAILABLE"),
        (LLMContentBlockedError(), 422, "LLM_CONTENT_BLOCKED"),
        (LLMEmptyResponseError(), 502, "LLM_EMPTY_RESPONSE"),
        (LLMError(), 502, "LLM_ERROR"),
    ],
)
def test_llm_failures_map_to_http_errors(client, auth_headers, fake_llm, error, status, code):
    fake_llm.error = error

    response = client.post("/api/query", json={"query": "hello"}, headers=auth_headers)

    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_unexpected_error_does_not_leak_details(client_factory, auth_headers, fake_llm):
    fake_llm.error = RuntimeError("secret internal detail")
    client = client_factory()
    client._transport.raise_server_exceptions = False  # type: ignore[attr-defined]

    response = client.post("/api/query", json={"query": "hello"}, headers=auth_headers)

    assert response.status_code == 500
    assert "secret internal detail" not in response.text
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"


def test_rate_limit_returns_429_with_retry_after(client_factory, auth_headers):
    client = client_factory(rate_limit_requests=2)

    for _ in range(2):
        assert client.post("/api/query", json={"query": "hi"}, headers=auth_headers).is_success

    response = client.post("/api/query", json={"query": "hi"}, headers=auth_headers)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert int(response.headers["Retry-After"]) >= 1


def test_cors_allows_configured_origin_only(client):
    allowed = client.options(
        "/api/query",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    blocked = client.options(
        "/api/query",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )

    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in blocked.headers
