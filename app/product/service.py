from app.category.repository import CategoryRepository
from .exceptions import ProductNotFound, CategoryNotFound
from uuid import uuid4
from .repository import ProductRepository
from sqlalchemy.orm import Session
from app.core.logger import get_logger
from .model import Product

logger = get_logger(__name__)

class ProductService:
    def __init__(self, db: Session): 
        self.repo = ProductRepository(db)
        self.category_repo = CategoryRepository()

    def create_product(self, db: Session, data):
        logger.info("Starting product creation", extra={"product_name": data.name, "category_id": str(data.category_id)})
        category = self.category_repo.get_by_id(db, data.category_id)
        if not category:
            logger.error("Product creation failed - Category not found", extra={"category_id": str(data.category_id)})
            raise CategoryNotFound("Category not found")
        product = Product(
            name = data.name,
            description = data.description,
            category_id = data.category_id
        )

        created = self.repo.create(product)
        logger.info("Product created successfully", extra={"product_id": str(created.id), "category_id": str(created.category_id)})
        return created

    def get_product(self, product_id):
        product = self.repo.get(product_id)
        if not product:
            logger.warning("Product lookup failed - not found", extra={"product_id": str(product_id)})
            raise ProductNotFound("Product not found")
        return product

    def delete_product(self, product_id):
        logger.info("Starting product deletion", extra={"product_id": str(product_id)})
        product = self.get_product(product_id)
        self.repo.delete(product)
        logger.info("Product deleted successfully", extra={"product_id": str(product_id)})

    def list_products(self, search, category_id, page, page_size):
        logger.info("Listing products", extra={"search": search, "category_id": str(category_id) if category_id else None, "page": page, "page_size": page_size})
        products, total = self.repo.list(search, category_id, page, page_size)
        logger.info("Products listed successfully", extra={"total_results": total, "retrieved_count": len(products)})
        return products, total