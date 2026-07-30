"""
Item Pydantic models with MongoDB ObjectId support.

MongoDB uses BSON ObjectId as the primary key (_id).
We map it explicitly to a plain string `id` in API responses
so clients never see MongoDB internals.
"""

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request schemas  (what clients send)
# ---------------------------------------------------------------------------


class ItemCreate(BaseModel):
    """Payload for creating a new item."""

    name: str = Field(..., min_length=1, max_length=200, examples=["Widget A"])
    description: str | None = Field(None, max_length=1000)
    price: float = Field(..., gt=0, examples=[9.99])
    is_active: bool = Field(True)


class ItemUpdate(BaseModel):
    """Payload for partially updating an item (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    price: float | None = Field(None, gt=0)
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Response schema  (what the API returns)
# ---------------------------------------------------------------------------


class ItemResponse(BaseModel):
    """
    Full item representation returned by the API.

    `id` is the MongoDB ObjectId serialised as a plain string.
    """

    id: str  # MongoDB _id mapped to id — clients see a plain string
    name: str
    description: str | None = None
    price: float
    is_active: bool


# ---------------------------------------------------------------------------
# Database document helper
# ---------------------------------------------------------------------------


def item_from_doc(doc: dict[str, Any]) -> ItemResponse:
    """Convert a raw MongoDB document dict to an ItemResponse."""
    return ItemResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        description=doc.get("description"),
        price=doc["price"],
        is_active=doc.get("is_active", True),
    )
