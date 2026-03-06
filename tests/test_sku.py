import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

class MockSKUResponse:
    def __init__(self, sku_code, price, quantity):
        self.id = uuid4()
        self.product_id = uuid4()
        self.sku_code = sku_code
        self.price = price
        self.quantity = quantity
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

@patch("app.sku.api.SKUService")
def test_create_sku(mock_service_class, client):
    mock_instance = MagicMock()
    mock_instance.create_sku.return_value = MockSKUResponse("SKU-123", 100, 50)
    mock_service_class.return_value = mock_instance

    response = client.post("/skus", json={
        "sku_code": "SKU-123",
        "price": 100,
        "quantity": 50,
        "product_id": str(uuid4())
    })
    
    assert response.status_code == 200
    assert response.json()["sku_code"] == "SKU-123"

@patch("app.sku.api.SKUService")
def test_update_sku(mock_service_class, client):
    mock_instance = MagicMock()
    mock_instance.update_sku.return_value = MockSKUResponse("SKU-123", 200, 100)
    mock_service_class.return_value = mock_instance

    sku_id = str(uuid4())
    response = client.put(f"/skus/{sku_id}", json={
        "price": 200,
        "quantity": 100
    })
    
    assert response.status_code == 200
    assert response.json()["price"] == 200
    assert response.json()["quantity"] == 100

@patch("app.sku.api.SKUService")
def test_delete_sku(mock_service_class, client):
    mock_instance = MagicMock()
    mock_instance.delete_sku.return_value = None
    mock_service_class.return_value = mock_instance

    sku_id = str(uuid4())
    response = client.delete(f"/skus/{sku_id}")
    
    assert response.status_code == 200
    assert response.json()["message"] == "SKU deleted successfully"

@patch("app.sku.api.SKUService")
def test_list_skus(mock_service_class, client):
    mock_instance = MagicMock()
    mock_instance.list_skus_by_product_id.return_value = [MockSKUResponse("SKU-1", 10, 5), MockSKUResponse("SKU-2", 20, 15)]
    mock_service_class.return_value = mock_instance

    product_id = str(uuid4())
    response = client.get(f"/skus/product/{product_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 2
    assert data["data"][0]["sku_code"] == "SKU-1"
