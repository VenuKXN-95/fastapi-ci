"""
Shared pytest fixtures.

Patches the MongoDB lifespan hooks (connect / close) so tests never
require a real MongoDB server. The actual DB calls go through the
`get_db` dependency override in each test module.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.database import get_db
from app.main import app


# ---------------------------------------------------------------------------
# Autouse: mock the MongoDB lifespan so startup never calls a real server
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def mock_mongo_lifecycle():
    """
    Replace connect_to_mongo / close_mongo_connection with no-ops
    so the FastAPI lifespan does not attempt a real network connection.
    """
    with (
        patch("app.main.connect_to_mongo", new_callable=AsyncMock),
        patch("app.main.close_mongo_connection", new_callable=AsyncMock),
    ):
        yield


# ---------------------------------------------------------------------------
# Shared mock database + HTTP client
# ---------------------------------------------------------------------------
@pytest.fixture
async def mock_db():
    """Yield a clean mongomock database, reset after each test."""
    client = AsyncMongoMockClient()
    db = client["test_fastapi_db"]
    yield db
    for name in await db.list_collection_names():
        await db.drop_collection(name)
    client.close()


@pytest.fixture
async def async_client(mock_db) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with get_db overridden to use the mongomock database."""

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
