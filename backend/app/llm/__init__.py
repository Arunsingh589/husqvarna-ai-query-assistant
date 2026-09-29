from app.core.config import Settings
from app.llm.base import LLMProvider, LLMResult, TokenUsage
from app.llm.openai_provider import OpenAIProvider

__all__ = ["LLMProvider", "LLMResult", "TokenUsage", "build_llm_provider"]


def build_llm_provider(settings: Settings) -> LLMProvider:
    return OpenAIProvider(settings)
