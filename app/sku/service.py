from app.sku.exceptions import SKUNotFound
from app.sku.exceptions import SKUAlreadyExists
from app.product.exceptions import ProductNotFound
from app.product.repository import ProductRepository
from app.sku.repository import SKURepository
from .model import SKU
class SKUService:
    def __init__(self, db):
        self.repo = SKURepository(db)
        self.product_repo = ProductRepository(db)
        self.db = db

    def create_sku(self, sku_data):
        product = self.product_repo.get(sku_data.product_id)
        if not product:
            raise ProductNotFound()

        if self.repo.get_by_sku_code(sku_data.sku_code):
            raise SKUAlreadyExists()

        sku = SKU(**sku_data.model_dump())
        self.repo.create(sku)

    def update_sku(self, sku_id, data):
        sku = self.repo.get_by_id(sku_id)
        if not sku:
            raise SKUNotFound()

        update_data = data.model_dump(exclude_unset = True)
        for key, value in update_data.items():
            setattr(sku, key, value)

        self.repo.commit()
        self.repo.refresh(sku)
        return sku

    def delete_sku(self, sku_id):
        sku = self.repo.get_by_id(sku_id)
        if not sku:
            raise SKUNotFound()

        self.repo.delete(sku)


    def list_skus_by_product_id(self, product_id):
        product = self.product_repo.get(product_id)
        if not product:
            raise ProductNotFound()

        return self.repo.list_by_product_id(product_id)