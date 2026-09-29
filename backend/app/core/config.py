from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "production", "test"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Query Assistant"
    app_env: Environment = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    jwt_secret: SecretStr = Field(min_length=32)
    jwt_issuer: str = "ai-query-assistant"
    jwt_audience: str = "ai-query-assistant-api"
    jwt_expire_minutes: int = Field(default=60, gt=0, le=24 * 60)

    openai_api_key: SecretStr = Field(min_length=1)
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    llm_max_output_tokens: int = Field(default=800, gt=0, le=8_000)
    llm_temperature: float | None = Field(default=0.3, ge=0, le=2)

    rate_limit_requests: int = Field(default=10, gt=0)
    rate_limit_window_seconds: int = Field(default=60, gt=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"
