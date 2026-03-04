from app.sku.service import SKUService
from app.core.database import get_db
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from .schema import SKUResponse, SKUCreate, SKUListResponse, SKUUpdate

router = APIRouter(prefix = "/skus", tags = ["SKUs"])

@router.post("", response_model = SKUResponse)
def create_sku(payload: SKUCreate, db: Session = Depends(get_db)):
    service = SKUService(db)
    return service.create_sku(payload)

@router.put("/{sku_id}", response_model = SKUResponse)
def update_sku(sku_id: str, payload: SKUUpdate, db: Session = Depends(get_db)):
    service = SKUService(db)
    return service.update_sku(sku_id, payload)

@router.delete("/{sku_id}")
def delete_sku(sku_id: str, db: Session = Depends(get_db)):
    service = SKUService(db)
    service.delete_sku(sku_id)
    return {"message": "SKU deleted successfully"}

@router.get("/product/{product_id}", response_model = SKUListResponse)
def list_skus(product_id: str, db: Session = Depends(get_db)):
    service = SKUService(db)
    skus = service.list_skus_by_product_id(product_id)
    return {"data": skus}



