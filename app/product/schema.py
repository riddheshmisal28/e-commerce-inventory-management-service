from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Optional

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

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    category_id: UUID

    @field_validator("name")
    @classmethod
    def trim_name(cls, v: str):
        return v.strip()
        
class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None