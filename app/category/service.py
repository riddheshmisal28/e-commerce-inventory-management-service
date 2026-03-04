from uuid import uuid4
from fastapi import HTTPException
from app.category.repository import CategoryRepository
from sqlalchemy.orm import Session
from .schema import CategoryCreate, CategoryUpdate
from .model import Category

class CategoryService:
    def __init__(self):
        self.repo = CategoryRepository()

    def create_category(self, db: Session, data: CategoryCreate) -> Category:
        existing = self.repo.get_by_name(db, data.name)
        if existing:
            raise HTTPException(
                status_code = 400,
                detail = "Category with this name already exists"
            )
        
        category = Category(
            id = uuid4(),
            name = data.name,
            description = data.description,
        )

        return self.repo.create(db, category)

    def get_category(self, db: Session, category_id):
        category = self.repo.get_by_id(db, category_id)
        if not category:
            raise HTTPException(
                status_code = 404,
                detail = "Category not found"
            )
        return category

    def list_categories(self, db: Session):
        return self.repo.list(db)

    def update_category(self, db: Session, category_id, data: CategoryUpdate):
        category = self.get_category(db, category_id)
        if data.name:
            category.name = data.name
        if data.description:
            category.description = data.description

        db.commit()
        db.refresh(category)
        return category

    def delete_category(self, db: Session, category_id):
        category = self.get_category(db, category_id)
        self.repo.delete(db, category)

    
