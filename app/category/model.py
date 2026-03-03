from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import mapped_column, Mapped, relationship
import uuid
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID

class Category(Base):
    __tablename__ = "categories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid = True), primary_key = True, default = uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique = True, nullable = False, index = True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default = datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default = datetime.utcnow, onupdate = datetime.utcnow)

    # Relationship
    products:Mapped[list["Product"]] = relationship("Product", back_populates="category", passive_deletes = True)