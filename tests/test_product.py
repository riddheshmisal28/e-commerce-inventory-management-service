import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

class MockProductResponse:
    def __init__(self, name):
        self.id = uuid4()
        self.category_id = uuid4()
        self.name = name
        self.description = "Test Product Description"

@patch("app.product.api.ProductService")
def test_create_product(mock_service_class, client):
    mock_instance = MagicMock()
    mock_instance.create_product.return_value = MockProductResponse("Test Phone")
    mock_service_class.return_value = mock_instance

    response = client.post("/products", json={"name": "Test Phone", "description": "Desc", "category_id": str(uuid4())})
    assert response.status_code == 200
    assert response.json()["name"] == "Test Phone"

@patch("app.product.api.ProductService")
def test_list_products(mock_service_class, client):
    mock_instance = MagicMock()
    # returns products, total
    mock_instance.list_products.return_value = ([MockProductResponse("Product 1"), MockProductResponse("Product 2")], 2)
    mock_service_class.return_value = mock_instance

    response = client.get("/products")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["data"]) == 2
    assert data["data"][0]["name"] == "Product 1"

@patch("app.product.api.ProductService")
def test_get_product(mock_service_class, client):
    mock_instance = MagicMock()
    mock_instance.get_product.return_value = MockProductResponse("Got Product")
    mock_service_class.return_value = mock_instance

    product_id = str(uuid4())
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Got Product"

@patch("app.product.api.ProductService")
def test_delete_product(mock_service_class, client):
    mock_instance = MagicMock()
    mock_instance.delete_product.return_value = None
    mock_service_class.return_value = mock_instance

    product_id = str(uuid4())
    response = client.delete(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Deleted successfully"
