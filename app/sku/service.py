from app.sku.exceptions import SKUNotFound
from app.sku.exceptions import SKUAlreadyExists
from app.product.exceptions import ProductNotFound
from app.product.repository import ProductRepository
from app.sku.repository import SKURepository
from .model import SKU
from app.core.logger import get_logger

logger = get_logger(__name__)

class SKUService:
    def __init__(self, db):
        self.repo = SKURepository(db)
        self.product_repo = ProductRepository(db)
        self.db = db

    def create_sku(self, sku_data):
        logger.info("Attempting to create SKU", extra={"sku_code": sku_data.sku_code, "product_id": str(sku_data.product_id)})
        product = self.product_repo.get(sku_data.product_id)
        if not product:
            logger.error("SKU creation failed: Product not found", extra={"product_id": str(sku_data.product_id)})
            raise ProductNotFound()

        if self.repo.get_by_sku_code(sku_data.sku_code):
            logger.error("SKU creation failed: SKU code already exists", extra={"sku_code": sku_data.sku_code})
            raise SKUAlreadyExists()

        sku = SKU(**sku_data.model_dump())
        self.repo.create(sku)
        logger.info("SKU created successfully", extra={"sku_id": str(sku.id), "sku_code": sku.sku_code})
        return sku

    def update_sku(self, sku_id, data):
        logger.info("Attempting to update SKU", extra={"sku_id": str(sku_id)})
        sku = self.repo.get_by_id(sku_id)
        if not sku:
            logger.error("SKU update failed: SKU not found", extra={"sku_id": str(sku_id)})
            raise SKUNotFound()

        update_data = data.model_dump(exclude_unset = True)
        if hasattr(data, "sku_code") and data.sku_code:
            existing = self.repo.get_by_sku_code(data.sku_code)
            if existing and existing.id != sku_id:
                logger.error("SKU update failed: SKU code already exists", extra={"sku_id": str(sku_id), "new_sku_code": data.sku_code})
                raise SKUAlreadyExists()
                
        for key, value in update_data.items():
            setattr(sku, key, value)

        self.repo.commit()
        self.repo.refresh(sku)
        logger.info("SKU updated successfully", extra={"sku_id": str(sku.id)})
        return sku

    def delete_sku(self, sku_id):
        logger.info("Attempting to delete SKU", extra={"sku_id": str(sku_id)})
        sku = self.repo.get_by_id(sku_id)
        if not sku:
            logger.error("SKU deletion failed: SKU not found", extra={"sku_id": str(sku_id)})
            raise SKUNotFound()

        self.repo.delete(sku)
        logger.info("SKU deleted successfully", extra={"sku_id": str(sku_id)})


    def list_skus_by_product_id(self, product_id):
        logger.info("Fetching SKUs for product", extra={"product_id": str(product_id)})
        product = self.product_repo.get(product_id)
        if not product:
            logger.error("SKU listing failed: Product not found", extra={"product_id": str(product_id)})
            raise ProductNotFound()

        skus = self.repo.list_by_product_id(product_id)
        logger.info("Fetched SKUs successfully", extra={"product_id": str(product_id), "count": len(skus)})
        return skus