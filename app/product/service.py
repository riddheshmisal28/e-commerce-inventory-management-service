from app.category.repository import CategoryRepository
from .exceptions import ProductNotFound, CategoryNotFound
from uuid import uuid4
from .repository import ProductRepository
from sqlalchemy.orm import Session
from .model import Product

class ProductService:
    def __init__(self, db: Session): 
        self.repo = ProductRepository(db)
        self.category_repo = CategoryRepository()

    def create_product(self, db: Session, data):
        category = self.category_repo.get_by_id(db, data.category_id)
        if not category:
            raise CategoryNotFound("Category not found")
        product = Product(
            name = data.name,
            description = data.description,
            category_id = data.category_id
        )

        return self.repo.create(product)

    def get_product(self, product_id):
        product = self.repo.get(product_id)
        if not product:
            raise ProductNotFound("Product not found")
        return product

    def delete_product(self, product_id):
        product = self.get_product(product_id)
        self.repo.delete(product)

    def list_products(self, search, category_id, page, page_size):
        return self.repo.list(search, category_id, page, page_size)