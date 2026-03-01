import string
import string
from uuid import UUID
from pydantic import BaseModel

class ProductResponse(BaseModel):
    id: UUID
    name: str
    description: str
    category_id: UUID

    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    data: list[ProductResponse]
    total: int
    page: int
    page_size: int