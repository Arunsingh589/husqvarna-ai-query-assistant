import logging
from typing import Any

import openai
from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.errors import (
    LLMContentBlockedError,
    LLMEmptyResponseError,
    LLMError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.base import LLMResult, TokenUsage
from app.llm.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class OpenAIProvider:
    def __init__(self, settings: Settings):
        self._model = settings.openai_model
        self._max_output_tokens = settings.llm_max_output_tokens
        self._temperature = settings.llm_temperature
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    async def complete(self, query: str) -> LLMResult:
        params: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "max_completion_tokens": self._max_output_tokens,
        }
        if self._temperature is not None:
            params["temperature"] = self._temperature

        try:
            completion = await self._client.chat.completions.create(**params)
        except openai.APITimeoutError as exc:
            raise LLMTimeoutError() from exc
        except openai.RateLimitError as exc:
            logger.warning("OpenAI rate limited: %s", _error_code(exc))
            raise LLMUnavailableError() from exc
        except (openai.APIConnectionError, openai.InternalServerError) as exc:
            logger.warning("OpenAI unavailable: %s", type(exc).__name__)
            raise LLMUnavailableError() from exc
        except (openai.AuthenticationError, openai.PermissionDeniedError) as exc:
            logger.error("OpenAI rejected our credentials: %s", _error_code(exc))
            raise LLMError() from exc
        except openai.BadRequestError as exc:
            if _error_code(exc) == "content_filter":
                raise LLMContentBlockedError() from exc
            logger.error("OpenAI rejected the request: %s", _error_code(exc))
            raise LLMError() from exc
        except openai.APIError as exc:
            logger.error("OpenAI API error: %s", type(exc).__name__)
            raise LLMError() from exc

        if not completion.choices:
            raise LLMEmptyResponseError()

        choice = completion.choices[0]
        if choice.finish_reason == "content_filter":
            raise LLMContentBlockedError()

        answer = (choice.message.content or "").strip()
        if not answer:
            if choice.message.refusal:
                raise LLMContentBlockedError()
            raise LLMEmptyResponseError()

        usage = completion.usage
        return LLMResult(
            answer=answer,
            model=completion.model,
            truncated=choice.finish_reason == "length",
            usage=(
                TokenUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )
                if usage
                else None
            ),
        )

    async def aclose(self) -> None:
        await self._client.close()


def _error_code(exc: openai.APIStatusError) -> str:
    return str(exc.code or exc.status_code)
