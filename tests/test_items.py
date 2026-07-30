"""
Items endpoint tests — MongoDB backed.

Uses mongomock-motor via conftest.py fixtures.
No real MongoDB required.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_items_empty(async_client: AsyncClient) -> None:
    """Items list should be empty on a fresh database."""
    response = await async_client.get("/api/v1/items")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_item(async_client: AsyncClient) -> None:
    """POST /items should return 201 with the created item."""
    payload = {
        "name": "Test Widget",
        "description": "A test widget",
        "price": 9.99,
        "is_active": True,
    }
    response = await async_client.post("/api/v1/items", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["price"] == payload["price"]
    assert "id" in data
    assert len(data["id"]) == 24  # MongoDB ObjectId is 24 hex chars


@pytest.mark.asyncio
async def test_get_item_not_found(async_client: AsyncClient) -> None:
    """Fetching a non-existent ObjectId should return 404."""
    fake_id = "000000000000000000000001"
    response = await async_client.get(f"/api/v1/items/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_object_id(async_client: AsyncClient) -> None:
    """An invalid ObjectId format should return 422."""
    response = await async_client.get("/api/v1/items/not-a-valid-id")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_and_retrieve_item(async_client: AsyncClient) -> None:
    """Create then GET an item — round-trip verification."""
    payload = {
        "name": "Persistent Widget",
        "description": "Round-trip test",
        "price": 19.99,
        "is_active": True,
    }
    create_resp = await async_client.post("/api/v1/items", json=payload)
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    get_resp = await async_client.get(f"/api/v1/items/{item_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == item_id
    assert get_resp.json()["name"] == payload["name"]


@pytest.mark.asyncio
async def test_update_item(async_client: AsyncClient) -> None:
    """PATCH /items/{id} should update only the provided fields."""
    create_resp = await async_client.post(
        "/api/v1/items",
        json={"name": "Old Name", "price": 5.00, "is_active": True},
    )
    item_id = create_resp.json()["id"]

    patch_resp = await async_client.patch(
        f"/api/v1/items/{item_id}", json={"name": "New Name", "price": 15.00}
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["name"] == "New Name"
    assert data["price"] == 15.00
    assert data["is_active"] is True  # unchanged field preserved


@pytest.mark.asyncio
async def test_update_item_not_found(async_client: AsyncClient) -> None:
    """PATCH on a non-existent item should return 404."""
    fake_id = "000000000000000000000002"
    response = await async_client.patch(
        f"/api/v1/items/{fake_id}", json={"name": "Ghost"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_item_no_fields(async_client: AsyncClient) -> None:
    """PATCH with empty body should return 422."""
    create_resp = await async_client.post(
        "/api/v1/items",
        json={"name": "Old", "price": 5.00},
    )
    item_id = create_resp.json()["id"]
    response = await async_client.patch(f"/api/v1/items/{item_id}", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_item(async_client: AsyncClient) -> None:
    """DELETE /items/{id} should return 204 and item should be gone."""
    create_resp = await async_client.post(
        "/api/v1/items",
        json={"name": "Delete Me", "price": 1.00, "is_active": True},
    )
    item_id = create_resp.json()["id"]

    delete_resp = await async_client.delete(f"/api/v1/items/{item_id}")
    assert delete_resp.status_code == 204

    get_resp = await async_client.get(f"/api/v1/items/{item_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_item_not_found(async_client: AsyncClient) -> None:
    """DELETE on a non-existent item should return 404."""
    fake_id = "000000000000000000000003"
    response = await async_client.delete(f"/api/v1/items/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_items_after_inserts(async_client: AsyncClient) -> None:
    """List should return all inserted items."""
    for i in range(3):
        await async_client.post(
            "/api/v1/items",
            json={"name": f"Item {i}", "price": float(i + 1)},
        )
    response = await async_client.get("/api/v1/items")
    assert response.status_code == 200
    assert len(response.json()) == 3
