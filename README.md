# AI Query Assistant

A small full stack app where a user types a question and gets an answer from an LLM (OpenAI).
The API is protected with JWT and handles the usual failure cases: bad input, timeouts, rate limits and upstream errors.

- **Frontend:** React 19 + TypeScript + Vite
- **Backend:** Python 3.12 + FastAPI
- **LLM:** OpenAI Chat Completions (`gpt-4o-mini` by default)
- **Auth:** JWT (HS256)
- **Container:** Docker (backend)

Deployment plan for AWS is in [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Setup

Requirements: Python 3.10+, Node 20+, an OpenAI API key (and Docker, to run the backend in a container).

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```bash
OPENAI_API_KEY=sk-...
JWT_SECRET=<random string, 32+ chars>   # python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Run locally

**Backend** (http://localhost:8000, Swagger docs at `/docs`)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

**Frontend** (http://localhost:5173)

```bash
cd frontend
npm install
npm run dev                     # /api is proxied to http://localhost:8000
```

## Run the backend with Docker

```bash
docker build -t ai-query-backend ./backend
docker run --env-file backend/.env -e APP_ENV=development -p 8000:8000 ai-query-backend
```

The image defaults to `APP_ENV=production`, which turns off `/docs` and the test-token endpoint.
`APP_ENV=development` keeps them on so the frontend (`npm run dev`) can use this container as its API.

**Checks**

```bash
cd backend && pytest && ruff check . && mypy app
cd frontend && npm run lint && npm run build
```

---

## Using the API

### 1. Get a token

The exercise allows a test token, so the backend has a development-only endpoint that issues one.
It is only mounted when `APP_ENV=development`.

```bash
curl -X POST http://localhost:8000/api/auth/token
# or: cd backend && python -m scripts.gen_token
```

### 2. Ask a question

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain JWT in two sentences."}'
```

```json
{
  "answer": "A JWT is ...",
  "model": "gpt-4o-mini-2024-07-18",
  "truncated": false,
  "usage": { "prompt_tokens": 95, "completion_tokens": 60, "total_tokens": 155 },
  "request_id": "d829fbf00bf14b45a73d898f849ab6e2"
}
```

You can also try every endpoint from the Swagger UI at http://localhost:8000/docs
(click **Authorize** and paste the token).

### Endpoints

| Method | Path              | Auth | Description                              |
|--------|-------------------|------|------------------------------------------|
| GET    | `/health`         | No   | Liveness check used by Docker / the load balancer |
| POST   | `/api/auth/token` | No   | Issues a test JWT (development only)      |
| POST   | `/api/query`      | Yes  | Sends the query to the LLM and returns the answer |

### Errors

Every error has the same shape, so the client can branch on `code`:

```json
{ "error": { "code": "LLM_TIMEOUT", "message": "The AI service took too long to respond. Please try again.", "request_id": "..." } }
```

| Status | Code                  | When |
|--------|-----------------------|------|
| 400    | `INVALID_REQUEST`     | Missing/empty query, wrong type, over 4,000 chars, unknown fields, malformed JSON |
| 401    | `UNAUTHORIZED`        | Missing, invalid or expired token |
| 422    | `LLM_CONTENT_BLOCKED` | OpenAI content filter blocked the request or answer |
| 429    | `RATE_LIMITED`        | More than 10 requests/minute for a user (`Retry-After` header is set) |
| 502    | `LLM_ERROR` / `LLM_EMPTY_RESPONSE` | OpenAI rejected the request, or returned nothing usable |
| 503    | `LLM_UNAVAILABLE`     | OpenAI is rate limiting us or is down |
| 504    | `LLM_TIMEOUT`         | OpenAI did not answer in time (after retries) |
| 500    | `INTERNAL_ERROR`      | Anything unexpected; details are only logged, never returned |

The `request_id` is also returned as the `X-Request-ID` header and appears on every log line for that request, so a user-reported error can be traced.

---

## Project structure

```
backend/
  app/
    main.py               app factory: middleware, CORS, routers
    schemas.py            request/response models (Pydantic)
    api/
      dependencies.py     auth, rate limit and LLM provider dependencies
      routes/             query, health, dev token
    core/
      config.py           settings from env, validated at startup
      security.py         JWT create/verify
      errors.py           error classes + handlers (single error format)
      rate_limit.py       in-memory sliding window limiter
      middleware.py       request id + access log
      logging.py
    llm/
      base.py             LLMProvider interface
      openai_provider.py  OpenAI implementation + error mapping
      prompts.py          system prompt
  tests/                  pytest (LLM is faked, no network calls)
  Dockerfile

frontend/
  src/
    api/                  fetch wrapper (timeout, error parsing), token cache, query call
    hooks/                useAskQuestion, useTypewriter
    components/           SplashScreen, QueryForm, QueryResult, AnswerCard, ErrorMessage, ...
    styles/global.css     design tokens
```

---

## Decisions and trade-offs

**FastAPI (Python) for the backend.** Async support fits an I/O-bound service that mostly waits on the LLM, and Pydantic gives request validation and typed settings with very little code.

**LLM behind an interface.** Routes depend on `LLMProvider`, not on the OpenAI SDK. Switching to Azure OpenAI, Anthropic or a local model means adding one class. It also makes the route easy to test with a fake provider.

**Mapping LLM failures to clear HTTP errors.** The OpenAI SDK's exceptions are translated into our own error types: timeout → 504, rate limit or outage → 503, content filter → 422, bad key or other rejection → 502. The client gets a stable `code` and a friendly message; the real reason (e.g. `insufficient_quota`) is only logged. The SDK retries 429/5xx/connection errors twice with backoff before we give up.

**Handling the LLM's response.** Empty answers are treated as errors, refusals and content-filter stops are reported as blocked, and `finish_reason == "length"` is returned as `truncated: true` so the UI can say the answer was cut short. Output is capped with `max_completion_tokens`.

**JWT.** HS256 with a shared secret from `.env`. The algorithm is fixed on verification (so `alg: none` or algorithm-switching tokens are rejected), and `exp`, `iss` and `aud` are required. In production the tokens would come from a real identity provider; see DEPLOYMENT.md.

**Secrets.** The OpenAI key and JWT secret are only read on the backend from environment variables, wrapped in `SecretStr` so they don't show up in logs or reprs. `.env` is git-ignored and never baked into the Docker image. The browser never sees the OpenAI key.

**Safe API exposure.** Input is validated (length limit, no unknown fields), there is a per-user rate limit to protect the OpenAI bill, CORS is restricted to the configured origin, `/docs` is disabled in production, and 500 errors never leak internals. Query text is not logged, only its length, since it may contain personal data.

**Settings validated at startup.** A missing API key or a short JWT secret stops the app from starting instead of failing on the first request.

**Frontend.** Plain React with CSS Modules, no UI framework, and a small typed API layer. The client timeout (65s) is slightly longer than the backend's worst case, so the backend's clearer 504 message reaches the user first. Answers are rendered as Markdown with `react-markdown`, which does not render raw HTML, so model output can't inject scripts. The typewriter animation is skipped for users with "reduced motion" enabled.

**Same-origin API.** In development Vite proxies `/api` to the backend, so the browser only talks to one origin. This matches how it would run behind CloudFront in production and avoids CORS in practice.

## Assumptions

- A single question and answer is enough. Each query is sent to the model on its own, and the UI shows the latest question and its answer.
- A test token is acceptable, so there is no user login. The frontend fetches a token from the dev endpoint on start-up and refreshes it on a 401.
- One backend instance, so an in-memory rate limiter is fine.

## What I would do with more time

- **Conversation mode:** keep a chat history on screen and send the last few messages as `history` so follow-up questions work (with a cap on messages and tokens).
- **Streaming responses** with Server-Sent Events, so the answer appears as it is generated instead of after the full response.
- **Real authentication** with Amazon Cognito (RS256 + JWKS), instead of the dev token endpoint.
- **Shared rate limiting** in Redis, or at the edge with AWS WAF, once there is more than one instance.
- **Frontend tests** (Vitest + React Testing Library) and a Playwright end-to-end test.
- **CI pipeline** running lint, type checks, tests and the Docker build on every PR.
- **Observability:** structured JSON logs, metrics for latency, error rate and token usage.
