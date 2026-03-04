from sqlalchemy.orm import Session
from .model import SKU

class SKURepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, sku: SKU):
        self.db.add(sku)
        self.db.commit()
        self.db.refresh(sku)
        return sku

    def get_by_id(self, sku_id):
        return self.db.query(SKU).filter(SKU.id == sku_id).first()

    def get_by_sku_code(self, sku_code):
        return self.db.query(SKU).filter(SKU.sku_code == sku_code).first()

    def list_by_product_id(self, product_id):
        return self.db.query(SKU).filter(SKU.product_id == product_id).all()

    def delete(self, sku: SKU):
        self.db.delete(sku)
        self.db.commit()

    def commit(self):
        self.db.commit()

    def refresh(self, sku: SKU):
        self.db.refresh(sku)
