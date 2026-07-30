"""
MongoDB Database Layer.

Manages the Motor (async MongoDB) client lifecycle.
The client is created once at startup and shared across all requests
via FastAPI dependency injection.
"""

from collections.abc import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

# ---------------------------------------------------------------------------
# Module-level client — shared across the entire app lifetime
# ---------------------------------------------------------------------------
_mongo_client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]


def get_mongo_client() -> AsyncIOMotorClient:  # type: ignore[type-arg]
    """Return the active Motor client. Raises if not yet initialised."""
    if _mongo_client is None:
        raise RuntimeError(
            "MongoDB client is not initialised. "
            "Ensure connect_to_mongo() ran at app startup."
        )
    return _mongo_client


async def connect_to_mongo() -> None:
    """Create the Motor client and verify connectivity (startup hook)."""
    global _mongo_client
    _mongo_client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5000,  # fail fast if DB unreachable
        maxPoolSize=10,
        minPoolSize=1,
    )
    # Ping the server to confirm connection before accepting traffic
    await _mongo_client.admin.command("ping")


async def close_mongo_connection() -> None:
    """Close the Motor client (shutdown hook)."""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None


def get_database() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    """Return the application database handle."""
    return get_mongo_client()[settings.MONGODB_DB_NAME]


async def get_db() -> (
    AsyncGenerator[AsyncIOMotorDatabase, None]  # type: ignore[type-arg]
):
    """
    FastAPI dependency that yields the database for a single request.

    Usage::

        @router.get("/items")
        async def list_items(db: AsyncIOMotorDatabase = Depends(get_db)):
            ...
    """
    yield get_database()
