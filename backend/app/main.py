import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, health, query
from app.core.config import Settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import REQUEST_ID_HEADER, register_middleware
from app.core.rate_limit import SlidingWindowRateLimiter
from app.llm import LLMProvider, build_llm_provider

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    llm_provider: LLMProvider | None = None,
) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        provider = llm_provider or build_llm_provider(settings)
        app.state.llm_provider = provider
        logger.info(
            "Starting %s env=%s model=%s",
            settings.app_name,
            settings.app_env,
            settings.openai_model,
        )
        try:
            yield
        finally:
            await provider.aclose()

    docs_enabled = settings.app_env != "production"
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.state.settings = settings
    app.state.rate_limiter = SlidingWindowRateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    register_exception_handlers(app)
    register_middleware(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER, "Retry-After"],
        max_age=600,
    )

    app.include_router(health.router)
    app.include_router(query.router)
    if settings.is_development:
        app.include_router(auth.router)

    return app


app = create_app()
