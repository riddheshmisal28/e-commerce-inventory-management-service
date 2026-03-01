from app.product.schema import ProductListResponse
from fastapi import APIRouter, Depends, Query


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=ProductListResponse)
def get_product():
    return {
        "data": [
            {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Product 1",
                "description": "Description 1",
                "category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 1
    }