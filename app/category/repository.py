from uuid import UUID
from sqlalchemy.orm import Session
from .model import Category

class CategoryRepository:
    def create(self, db: Session, category: Category) -> Category:
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
        db.delete(category)
        db.commit()