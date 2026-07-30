"""
Items endpoint tests.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_items_empty() -> None:
    """Items list should be empty initially."""
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    assert response.json() == []


def test_create_item() -> None:
    """Creating an item should return 201 with the new item."""
    payload = {
        "name": "Test Widget",
        "description": "A test widget",
        "price": 9.99,
        "is_active": True,
    }
    response = client.post("/api/v1/items", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["price"] == payload["price"]
    assert "id" in data


def test_get_item_not_found() -> None:
    """Fetching a non-existent item should return 404."""
    response = client.get("/api/v1/items/99999")
    assert response.status_code == 404


def test_create_and_retrieve_item() -> None:
    """Create then retrieve an item to verify round-trip."""
    payload = {
        "name": "Persistent Widget",
        "description": "Round-trip test",
        "price": 19.99,
        "is_active": True,
    }
    create_resp = client.post("/api/v1/items", json=payload)
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/items/{item_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == item_id
    assert get_resp.json()["name"] == payload["name"]


def test_delete_item() -> None:
    """Delete an item should return 204."""
    payload = {
        "name": "Delete Me",
        "description": "Will be deleted",
        "price": 1.00,
        "is_active": True,
    }
    create_resp = client.post("/api/v1/items", json=payload)
    item_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/v1/items/{item_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/api/v1/items/{item_id}")
    assert get_resp.status_code == 404
