from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import datetime

class SKUBase(BaseModel):
    sku_code: str = Field(min_length = 1, max_length = 100)
    price: int = Field(gt = 0)
    quantity: int = Field(ge = 0)

class SKUCreate(SKUBase):
    product_id: UUID

class SKUUpdate(BaseModel):
    sku_code: Optional[str] = Field(None, min_length = 1, max_length = 100)
    price: Optional[int] = Field(None, gt = 0)
    quantity: Optional[int] = Field(None, ge = 0)

class SKUResponse(SKUBase):
    id: UUID
    product_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SKUListResponse(BaseModel):
    data: list[SKUResponse]
