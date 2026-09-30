"""Pytest configuration and client fixtures."""

import pytest
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
import httpx

from backend.app.main import create_app


@pytest.fixture(scope="session")
def app():
    """Create test application instance."""
    return create_app()


@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """Synchronous test client fixture."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client(app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Asynchronous test client fixture."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
