from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class LLMResult:
    answer: str
    model: str
    truncated: bool
    usage: TokenUsage | None


class LLMProvider(Protocol):
    async def complete(self, query: str) -> LLMResult: ...

    async def aclose(self) -> None: ...
