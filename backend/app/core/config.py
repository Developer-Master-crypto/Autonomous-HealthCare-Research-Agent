"""Global application configuration using Pydantic Settings."""

from typing import List, Union
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
        "*",  # Permissive in development for local file:// testing
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Database & Storage Abstraction (Supabase / Postgres)
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")
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


settings = Settings()
