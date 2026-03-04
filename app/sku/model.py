from datetime import datetime
from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

class SKU(Base):
    __tablename__ = "skus"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid = True), primary_key = True, default = uuid.uuid4)
    sku_code: Mapped[str] = mapped_column(String(100), unique = True, nullable = False, index = True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid = True), ForeignKey("products.id", ondelete = "CASCADE"), nullable = False)
    price: Mapped[int] = mapped_column(nullable = False)
    quantity: Mapped[int] = mapped_column(nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default = datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default = datetime.utcnow, onupdate = datetime.utcnow)

    product = relationship("Product", back_populates = "skus")