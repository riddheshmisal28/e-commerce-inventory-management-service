from uuid import UUID
from app.core.database import get_db
from fastapi import Depends
from sqlalchemy.orm import Session
from app.category.service import CategoryService
from fastapi import APIRouter
from .schema import CategoryResponse, CategoryUpdate, CategoryCreate
from typing import List


router = APIRouter(prefix = "/categories", tags = ["Categories"])
service = CategoryService()

@router.post("/", response_model = CategoryResponse)
def create_Category(
    payload: CategoryCreate,
    db: Session = Depends(get_db)
):
    return service.create_category(db, payload)


@router.get("/{category_id}", response_model = CategoryResponse)
def get_category(
    category_id: UUID,
    db: Session = Depends(get_db)
):
    return service.get_category(db, category_id)

@router.get("/", response_model = List[CategoryResponse])
def list_categories(
    db: Session = Depends(get_db)
):
    return service.list_categories(db)

@router.put("/{category_id}", response_model = CategoryResponse)
def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    db: Session = Depends(get_db)
):
    return service.update_category(db, category_id, payload)

@router.delete("/{category_id}", status_code = 204)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db)
):
    service.delete_category(db, category_id)
