from app.product.service import ProductService
from app.core.database import get_db
from sqlalchemy.orm import Session
from .schema import ProductListResponse, ProductResponse, ProductCreate
from fastapi import APIRouter, Depends, Query


router = APIRouter(prefix="/products", tags=["Products"])

@router.post("", response_model=ProductResponse)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    service = ProductService(db)
    return service.create_product(db, payload)


@router.get("", response_model=ProductListResponse)
def list_products(
    search: str | None = None,
    category_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
): 
    service = ProductService(db)
    products, total = service.list_products(search, category_id, page, page_size)

    return {
        "data": products,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    service = ProductService(db)
    return service.get_product(product_id)

@router.delete("/{product_id}")
def delete_product(product_id: str, db: Session = Depends(get_db)):
    service = ProductService(db)
    service.delete_product(product_id)
    return {"message": "Deleted successfully"}