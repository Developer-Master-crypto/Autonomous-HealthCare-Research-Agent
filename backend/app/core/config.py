"""Global application configuration using Pydantic Settings."""

from typing import List, Union
from urllib.parse import urlparse
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project metadata
    PROJECT_NAME: str = "ResearchOps API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server settings
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    # CORS settings
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = [origin.strip() for origin in v.split(",") if origin.strip()]
        for origin in v:
            parsed = urlparse(origin)
            if (origin == "*" or parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or parsed.username or parsed.password or parsed.path not in {"", "/"}
                    or parsed.query or parsed.fragment):
                raise ValueError("ALLOWED_ORIGINS must contain explicit HTTP(S) origins; wildcards are not allowed.")
        return v

    # Database & Storage Abstraction (Supabase / Postgres)
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")
    SUPABASE_SCHEMA: str = Field(default="public")
    DATABASE_URL: str = Field(default="")

    # AI Provider Abstraction Defaults
    DEFAULT_LLM_PROVIDER: str = "gemini"
    DEFAULT_MODEL: str = "gemini-2.5-flash"
    DEFAULT_TEMPERATURE: float = 0.2

    # Provider API keys (loaded strictly from environment, never hardcoded)
    GEMINI_API_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")
    ANTHROPIC_API_KEY: str = Field(default="")
    GROQ_API_KEY: str = Field(default="")

    # Search provider settings
    SEARCH_PROVIDER: str = "tavily"
    TAVILY_API_KEY: str = Field(default="")
    SEARCH_TIMEOUT_SECONDS: float = Field(default=15.0, gt=0, le=60)
    SEARCH_MAX_RESULTS: int = Field(default=10, ge=1, le=20)
    SOURCE_FETCH_TIMEOUT_SECONDS: float = Field(default=15.0, gt=0, le=60)
    MAX_SOURCE_CONTENT_CHARS: int = Field(default=12000, ge=1, le=100000)
    RESEARCH_RATE_LIMIT_PER_MINUTE: int = Field(default=20, ge=1, le=600)


settings = Settings()
