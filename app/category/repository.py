from uuid import UUID
from sqlalchemy.orm import Session
from .model import Category
from app.core.logger import get_logger

logger = get_logger(__name__)

class CategoryRepository:
    def create(self, db: Session, category: Category) -> Category:
        logger.info("Executing DB insert for category", extra={"category_id": str(category.id)})
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    def get_by_id(self, db: Session, category_id: UUID) -> Category | None:
        return db.get(Category, category_id)

    def get_by_name(self, db: Session, name: str) -> Category | None:
        return db.query(Category).filter(Category.name == name).first()

    def list(self, db: Session) -> list[Category]:
        return db.query(Category).all()

    def delete(self, db: Session, category: Category) -> None:
        logger.info("Executing DB delete for category", extra={"category_id": str(category.id)})
        db.delete(category)
        db.commit()