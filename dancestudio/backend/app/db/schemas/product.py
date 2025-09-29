from pydantic import BaseModel


class ProductBase(BaseModel):
    type: str
    name: str
    description: str | None = None
    price: float
    classes_count: int | None = None
    validity_days: int | None = None
    direction_limit_id: int | None = None
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    type: str | None = None
    name: str | None = None
    description: str | None = None
    price: float | None = None
    classes_count: int | None = None
    validity_days: int | None = None
    direction_limit_id: int | None = None
    is_active: bool | None = None


class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True
