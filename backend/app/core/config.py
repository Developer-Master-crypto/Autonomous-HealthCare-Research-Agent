"""Global application configuration using Pydantic Settings."""

from typing import List, Literal, Union
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
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
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="", repr=False)
    SUPABASE_SCHEMA: str = Field(default="public")

    # Search provider settings
    TAVILY_API_KEY: str = Field(default="")
    SEARCH_TIMEOUT_SECONDS: float = Field(default=15.0, gt=0, le=60)
    SEARCH_MAX_RESULTS: int = Field(default=10, ge=1, le=20)
    SOURCE_FETCH_TIMEOUT_SECONDS: float = Field(default=15.0, gt=0, le=60)
    MAX_SOURCE_CONTENT_CHARS: int = Field(default=12000, ge=1, le=100000)
    RESEARCH_RATE_LIMIT_PER_MINUTE: int = Field(default=20, ge=1, le=600)
    GEOCODING_PROVIDER: Literal["mock", "nominatim"] = "mock"

    @model_validator(mode="after")
    def require_live_integrations_in_production(self) -> "Settings":
        if self.ENVIRONMENT.casefold() == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be false when ENVIRONMENT=production.")
            if not self.SUPABASE_URL.strip() or not self.SUPABASE_SERVICE_ROLE_KEY.strip() or "placeholder" in self.SUPABASE_SERVICE_ROLE_KEY.casefold():
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required in production; in-memory storage is not allowed.")
            if not self.TAVILY_API_KEY.strip() or "placeholder" in self.TAVILY_API_KEY.casefold():
                raise ValueError("TAVILY_API_KEY is required in production; unconfigured search is not allowed.")
            if self.GEOCODING_PROVIDER != "nominatim":
                raise ValueError("GEOCODING_PROVIDER=nominatim is required in production; mock geocoding is not allowed.")
            local_hosts = {"localhost", "127.0.0.1", "::1"}
            if not any(urlparse(origin).hostname not in local_hosts for origin in self.ALLOWED_ORIGINS):
                raise ValueError("ALLOWED_ORIGINS must include the deployed frontend origin in production.")
        return self


settings = Settings()
