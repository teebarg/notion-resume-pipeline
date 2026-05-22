from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "notion-resume-api"
    debug: bool = False
    log_level: str = "INFO"

    host: str = "0.0.0.0"
    port: int = 8000
    api_v1_prefix: str = "/api/v1"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    redis_url: str = "redis://localhost:6379/0"
    redis_job_queue: str = "resume_jobs"

    NOTION_API_TOKEN: str = ""
    NOTION_API_VERSION: str = "2022-06-28"

    job_result_ttl_seconds: int = 86400
    job_poll_interval_ms: int = 500

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()