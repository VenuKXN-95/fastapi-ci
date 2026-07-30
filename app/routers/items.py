"""
Items router.

Demonstrates a standard CRUD resource endpoint pattern.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ItemBase(BaseModel):
    """Base item schema."""

    name: str
    description: Optional[str] = None
    price: float
    is_active: bool = True


class ItemCreate(ItemBase):
    """Schema for creating an item."""


class ItemResponse(ItemBase):
    """Schema for item responses."""

    id: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# In-memory store (replace with real DB layer)
# ---------------------------------------------------------------------------
_store: dict[int, ItemResponse] = {}
_counter: int = 0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/items", response_model=List[ItemResponse], summary="List all items")
async def list_items() -> List[ItemResponse]:
    """Return all stored items."""
    return list(_store.values())


@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an item",
)
async def create_item(payload: ItemCreate) -> ItemResponse:
    """Create and store a new item."""
    global _counter
    _counter += 1
    item = ItemResponse(id=_counter, **payload.model_dump())
    _store[_counter] = item
    return item


@router.get("/items/{item_id}", response_model=ItemResponse, summary="Get item by ID")
async def get_item(item_id: int) -> ItemResponse:
    """Retrieve a single item by its ID."""
    if item_id not in _store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id={item_id} not found",
        )
    return _store[item_id]


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
)
async def delete_item(item_id: int) -> None:
    """Delete an item by its ID."""
    if item_id not in _store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id={item_id} not found",
        )
    del _store[item_id]
