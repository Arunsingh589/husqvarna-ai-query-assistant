from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MAX_QUERY_LENGTH = 4_000

QueryText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUERY_LENGTH),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QueryRequest(StrictModel):
    query: QueryText = Field(description="The question to send to the AI assistant.")


class UsageOut(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class QueryResponse(BaseModel):
    answer: str
    model: str
    truncated: bool = Field(description="True if the answer hit the output token limit.")
    usage: UsageOut | None
    request_id: str


class TokenRequest(StrictModel):
    subject: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
    ] = "test-user"


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None
    details: list[dict[str, str]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
