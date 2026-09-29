from datetime import datetime, timedelta, timezone

import jwt
import pytest

from tests.conftest import TEST_SECRET

QUERY = {"query": "What is the capital of France?"}


def _token(**overrides: object) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "test-user",
        "iss": "ai-query-assistant",
        "aud": "ai-query-assistant-api",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        **overrides,
    }
    return jwt.encode(claims, TEST_SECRET, algorithm="HS256")


def test_missing_token_is_rejected(client):
    response = client.post("/api/query", json=QUERY)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        jwt.encode({"sub": "x"}, "some-other-secret-that-is-long-enough!!", algorithm="HS256"),
        _token(aud="someone-else"),
        _token(iss="someone-else"),
    ],
    ids=["garbage", "wrong-secret", "wrong-audience", "wrong-issuer"],
)
def test_invalid_tokens_are_rejected(client, token):
    response = client.post("/api/query", json=QUERY, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_unsigned_alg_none_token_is_rejected(client):
    token = jwt.encode({"sub": "attacker"}, key=None, algorithm="none")

    response = client.post("/api/query", json=QUERY, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_expired_token_is_rejected(client):
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    token = _token(iat=past - timedelta(minutes=5), exp=past)

    response = client.post("/api/query", json=QUERY, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert "expired" in response.json()["error"]["message"]


def test_dev_token_endpoint_issues_usable_token(client):
    token_response = client.post("/api/auth/token", json={"subject": "alice"})
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]

    response = client.post("/api/query", json=QUERY, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_dev_token_endpoint_accepts_empty_body(client):
    response = client.post("/api/auth/token")

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_dev_token_endpoint_is_disabled_in_production(client_factory):
    client = client_factory(app_env="production")

    assert client.post("/api/auth/token").status_code == 404
    assert client.get("/docs").status_code == 404
