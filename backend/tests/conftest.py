import os

# app.main creates the app on import
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-definitely-long-enough-123")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import create_access_token
from app.llm import LLMResult, TokenUsage
from app.main import create_app

TEST_SECRET = "test-secret-that-is-definitely-long-enough-123"


class FakeLLM:
    def __init__(self) -> None:
        self.error: Exception | None = None
        self.result = LLMResult(
            answer="Paris is the capital of France.",
            model="fake-model",
            truncated=False,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=7, total_tokens=17),
        )
        self.calls: list[str] = []

    async def complete(self, query: str) -> LLMResult:
        self.calls.append(query)
        if self.error:
            raise self.error
        return self.result

    async def aclose(self) -> None:
        return None


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "development",
        "jwt_secret": TEST_SECRET,
        "openai_api_key": "sk-test",
        "rate_limit_requests": 100,
        **overrides,
    }
    return Settings(_env_file=None, **values)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client_factory(fake_llm: FakeLLM) -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []

    def factory(**overrides: Any) -> TestClient:
        client = TestClient(create_app(make_settings(**overrides), llm_provider=fake_llm))
        client.__enter__()
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(client_factory: Callable[..., TestClient]) -> TestClient:
    return client_factory()


@pytest.fixture
def auth_headers(settings: Settings) -> dict[str, str]:
    token, _ = create_access_token("test-user", settings)
    return {"Authorization": f"Bearer {token}"}
