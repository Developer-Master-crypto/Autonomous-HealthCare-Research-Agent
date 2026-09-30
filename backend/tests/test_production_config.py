"""Production settings must not silently select development substitutes."""

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_production_requires_live_search_persistence_and_geocoding():
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        Settings(ENVIRONMENT="production")

    with pytest.raises(ValidationError, match="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required"):
        Settings(ENVIRONMENT="production", DEBUG=False)

    with pytest.raises(ValidationError, match="TAVILY_API_KEY is required"):
        Settings(ENVIRONMENT="production", DEBUG=False,
                 SUPABASE_URL="https://project.supabase.co", SUPABASE_SERVICE_ROLE_KEY="server-secret")

    with pytest.raises(ValidationError, match="GEOCODING_PROVIDER=nominatim is required"):
        Settings(ENVIRONMENT="production", DEBUG=False,
                 SUPABASE_URL="https://project.supabase.co", SUPABASE_SERVICE_ROLE_KEY="server-secret",
                 TAVILY_API_KEY="search-secret")


def test_production_accepts_configured_live_providers():
    settings = Settings(ENVIRONMENT="production", DEBUG=False,
                        SUPABASE_URL="https://project.supabase.co", SUPABASE_SERVICE_ROLE_KEY="server-secret",
                        TAVILY_API_KEY="search-secret", GEOCODING_PROVIDER="nominatim",
                        ALLOWED_ORIGINS="https://research.example")
    assert settings.GEOCODING_PROVIDER == "nominatim"
