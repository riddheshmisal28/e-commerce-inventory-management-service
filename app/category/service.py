from uuid import uuid4
from fastapi import HTTPException
from app.category.repository import CategoryRepository
from sqlalchemy.orm import Session
from .schema import CategoryCreate, CategoryUpdate
from .model import Category
from app.core.logger import get_logger

logger = get_logger(__name__)

class CategoryService:
    def __init__(self):
        self.repo = CategoryRepository()

    def create_category(self, db: Session, data: CategoryCreate) -> Category:
        logger.info("Attempting to create category", extra={"name": data.name})
        existing = self.repo.get_by_name(db, data.name)
        if existing:
            logger.error("Category creation failed: Name already exists", extra={"name": data.name})
            raise HTTPException(
                status_code = 400,
                detail = "Category with this name already exists"
            )
        
        category = Category(
            id = uuid4(),
            name = data.name,
            description = data.description,
        )

        result = self.repo.create(db, category)
        logger.info("Category created successfully", extra={"category_id": str(result.id)})
        return result

    def get_category(self, db: Session, category_id):
        category = self.repo.get_by_id(db, category_id)
        if not category:
            logger.warning("Category lookup failed: not found", extra={"category_id": str(category_id)})
            raise HTTPException(
                status_code = 404,
                detail = "Category not found"
            )
        return category

    def list_categories(self, db: Session):
        categories = self.repo.list(db)
        logger.info("Listed categories", extra={"count": len(categories)})
        return categories

    def update_category(self, db: Session, category_id, data: CategoryUpdate):
        logger.info("Attempting to update category", extra={"category_id": str(category_id)})
        category = self.get_category(db, category_id)
        if data.name:
            category.name = data.name
        if data.description:
            category.description = data.description

        db.commit()
        db.refresh(category)
        logger.info("Category updated successfully", extra={"category_id": str(category_id)})
        return category

    def delete_category(self, db: Session, category_id):
        logger.info("Attempting to delete category", extra={"category_id": str(category_id)})
        category = self.get_category(db, category_id)
        self.repo.delete(db, category)
        logger.info("Category deleted successfully", extra={"category_id": str(category_id)})

    
