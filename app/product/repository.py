from sqlalchemy.orm import Session
from .model import Product
from sqlalchemy import select, func
from app.core.logger import get_logger

logger = get_logger(__name__)

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, product: Product):
        logger.info("Executing DB insert for product", extra={"product_id": str(product.id) if product.id else None})
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get(self, product_id):
        return self.db.get(Product, product_id)

    def delete(self, product: Product):
        logger.info("Executing DB delete for product", extra={"product_id": str(product.id)})
        self.db.delete(product)
        self.db.commit()

    def list(self, search, category_id, page, page_size):
        query = select(Product)

        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))

        if category_id:
            query = query.where(Product.category_id == category_id)

        total = self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )

        query = query.offset((page - 1) * page_size).limit(page_size)

        result = self.db.scalars(query).all()

        return result, total

