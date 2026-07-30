"""
Items router — MongoDB backed.

Full async CRUD using Motor (async MongoDB driver).
The collection name is `items` in the database configured via MONGODB_DB_NAME.
"""

from typing import List

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.item import ItemCreate, ItemResponse, ItemUpdate, item_from_doc

router = APIRouter()

COLLECTION = "items"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _object_id(item_id: str) -> ObjectId:
    """Convert a string to ObjectId, raising 422 on invalid format."""
    try:
        return ObjectId(item_id)
    except (InvalidId, Exception):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{item_id}' is not a valid MongoDB ObjectId.",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/items",
    response_model=List[ItemResponse],
    summary="List all items",
)
async def list_items(
    db: AsyncIOMotorDatabase = Depends(get_db),  # type: ignore[type-arg]
) -> List[ItemResponse]:
    """Return all items from MongoDB."""
    cursor = db[COLLECTION].find()
    docs = await cursor.to_list(length=1000)
    return [item_from_doc(doc) for doc in docs]


@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an item",
)
async def create_item(
    payload: ItemCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),  # type: ignore[type-arg]
) -> ItemResponse:
    """Insert a new item into MongoDB and return it with its generated _id."""
    doc = payload.model_dump()
    result = await db[COLLECTION].insert_one(doc)
    created = await db[COLLECTION].find_one({"_id": result.inserted_id})
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Item was inserted but could not be retrieved.",
        )
    return item_from_doc(created)


@router.get(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="Get item by ID",
)
async def get_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),  # type: ignore[type-arg]
) -> ItemResponse:
    """Fetch a single item by its MongoDB ObjectId string."""
    doc = await db[COLLECTION].find_one({"_id": _object_id(item_id)})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' not found.",
        )
    return item_from_doc(doc)


@router.patch(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="Partially update an item",
)
async def update_item(
    item_id: str,
    payload: ItemUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),  # type: ignore[type-arg]
) -> ItemResponse:
    """Update only the provided fields of an existing item."""
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update.",
        )
    result = await db[COLLECTION].update_one(
        {"_id": _object_id(item_id)},
        {"$set": updates},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' not found.",
        )
    updated = await db[COLLECTION].find_one({"_id": _object_id(item_id)})
    return item_from_doc(updated)  # type: ignore[arg-type]


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
)
async def delete_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),  # type: ignore[type-arg]
) -> None:
    """Delete an item by its MongoDB ObjectId."""
    result = await db[COLLECTION].delete_one({"_id": _object_id(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' not found.",
        )
