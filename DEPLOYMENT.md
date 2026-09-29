# Deployment on AWS

This is how I would run the app on AWS using the existing backend Docker image. It is a plan, not something that has been deployed.

## Overview

```
                      Route 53 (app.example.com)
                                 │
                           CloudFront + WAF
                  ┌──────────────┴───────────────┐
             /* (static)                    /api/* , /health
                  │                              │
          S3 bucket (React build)     Application Load Balancer (HTTPS)
                                                 │
                                   ECS Fargate service (backend)
                                   2+ tasks across 2 AZs, private subnets
                                                 │
                                    NAT Gateway ──► api.openai.com

  ECR ── backend image          Secrets Manager ── OPENAI_API_KEY, JWT_SECRET
  CloudWatch ── logs, metrics, alarms
```

The browser only talks to one domain. CloudFront serves the static frontend from S3 and forwards `/api/*` to the load balancer (the same idea as the Vite dev proxy), so there is no CORS to configure.

## Components

| Component | Service | Notes |
|---|---|---|
| Backend image | **ECR** | Tagged with the git commit SHA. Image scanning on push. |
| Backend runtime | **ECS on Fargate** | No servers to manage. The container already runs as non-root and has a health check. |
| Load balancer | **ALB** | HTTPS with an ACM certificate; health check on `GET /health`. |
| Frontend | **S3 + CloudFront** | Static build, long cache for hashed assets, no cache for `index.html`. Bucket is private (Origin Access Control). |
| Secrets | **Secrets Manager** | `OPENAI_API_KEY` and `JWT_SECRET` injected into the task as environment variables at start-up. Never in the image or the repo. |
| Edge protection | **AWS WAF** | Managed rule sets plus a rate-based rule on `/api/*`. |
| DNS / TLS | **Route 53 + ACM** | |
| Logs and metrics | **CloudWatch** | `awslogs` driver, one log group per service. |

## Networking

- VPC across two Availability Zones.
- ECS tasks run in **private subnets** with no public IP. Outbound calls to OpenAI go through a **NAT Gateway**.
- The ALB is the only thing in the public subnets.
- Security groups: the ALB accepts 443 from CloudFront only (using the CloudFront managed prefix list); tasks accept 8000 from the ALB only.

## Backend service

**Task definition (starting point)**

- 0.5 vCPU, 1 GB memory. The service mostly waits on OpenAI, so it is light on CPU.
- Environment: `APP_ENV=production`, `CORS_ORIGINS=https://app.example.com`, model and timeout settings.
- Secrets: `OPENAI_API_KEY`, `JWT_SECRET` from Secrets Manager. The task execution role gets `secretsmanager:GetSecretValue` on those two secrets only.
- `APP_ENV=production` also turns off `/docs` and the test-token endpoint.

**Scaling**

- Minimum 2 tasks (one per AZ) for availability.
- Target tracking on ALB requests per target and CPU, up to e.g. 10 tasks.

**Timeouts**

The LLM call is the slow part, so the timeouts have to line up from the outside in:

- CloudFront origin response timeout: 60s (default is 30s).
- ALB idle timeout: 90s.
- In production I would set `LLM_TIMEOUT_SECONDS=20` and `LLM_MAX_RETRIES=1`, so the worst case stays around 45s and the backend's own 504 is returned before any proxy gives up.

## Authentication in production

The dev token endpoint is disabled in production. Users would sign in through **Amazon Cognito** (or the company's existing identity provider). The frontend gets a token from Cognito, and the backend verifies it with **RS256** using Cognito's public keys (JWKS) instead of a shared secret. The code change is contained in `app/core/security.py`; the rest of the app only depends on `get_current_subject`.

## Rate limiting with more than one task

The in-app rate limiter is per task, so with N tasks the real limit is N times higher. In production:

- The WAF rate-based rule gives a coarse limit per IP at the edge.
- For an exact per-user limit, move the limiter to **ElastiCache (Redis)**.

## Observability

- **Logs:** each line carries the request id, which is also returned to the client, so a reported error can be found quickly. Query text is never logged.
- **Metrics and alarms:** ALB 5xx rate, target response time (p95), unhealthy host count, ECS CPU and memory.
- **LLM usage:** token counts are logged per request. A CloudWatch metric filter on them gives a cost dashboard, and an alarm on spikes catches abuse early.
- **OpenAI budget:** usage limits set on the OpenAI account as a last line of defence.

## CI/CD (GitHub Actions)

On every pull request:

1. Backend: `ruff`, `mypy`, `pytest`.
2. Frontend: `npm run lint`, `npm run build`.
3. `docker build` for the backend image.

On merge to `main`:

1. Authenticate to AWS with **GitHub OIDC** (no long-lived AWS keys stored in GitHub).
2. Build the backend image, tag it with the commit SHA and push it to ECR.
3. Register a new task definition revision with that image and update the ECS service (rolling deployment with the **deployment circuit breaker** enabled, so a failing release is rolled back automatically).
4. Build the frontend, `aws s3 sync` to the bucket, and invalidate `index.html` in CloudFront.

Staging and production are separate environments; production deploys need a manual approval step.

## Infrastructure as code

Everything above would be defined in **Terraform** (or AWS CDK), with one state per environment, so the setup is reviewable and repeatable instead of built by hand in the console.
