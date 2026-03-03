from .exceptions import ProductNotFound
from uuid import uuid4
from .repository import ProductRepository
from sqlalchemy.orm import Session
from .model import Product

class ProductService:
    def __init__(self, db: Session): 
        self.repo = ProductRepository(db)

    def create_product(self, data):
        
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