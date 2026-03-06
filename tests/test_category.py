import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from uuid import uuid4

# We patch the service used in app.category.api
from app.category.api import service as category_service

def mock_category(name):
    return {
        "id": str(uuid4()),
        "name": name,
        "description": "Test description",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

class MockCategoryResponse:
    def __init__(self, name):
        self.id = uuid4()
        self.name = name
        self.description = "Test description"
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

@patch.object(category_service, 'create_category')
def test_create_category(mock_create, client):
    mock_create.return_value = MockCategoryResponse("Electronics")
    response = client.post("/categories/", json={"name": "Electronics", "description": "Test"})
    assert response.status_code == 200
    assert response.json()["name"] == "Electronics"

@patch.object(category_service, 'get_category')
def test_get_category(mock_get, client):
    mock_get.return_value = MockCategoryResponse("Electronics")
    cat_id = str(uuid4())
    response = client.get(f"/categories/{cat_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Electronics"

@patch.object(category_service, 'list_categories')
def test_list_categories(mock_list, client):
    mock_list.return_value = [MockCategoryResponse("Electronics"), MockCategoryResponse("Books")]
    response = client.get("/categories/")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Electronics"

@patch.object(category_service, 'update_category')
def test_update_category(mock_update, client):
    mock_update.return_value = MockCategoryResponse("Updated")
    cat_id = str(uuid4())
    response = client.put(f"/categories/{cat_id}", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"

@patch.object(category_service, 'delete_category')
def test_delete_category(mock_delete, client):
    mock_delete.return_value = None
    cat_id = str(uuid4())
    response = client.delete(f"/categories/{cat_id}")
    assert response.status_code == 204
