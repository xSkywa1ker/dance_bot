from pydantic import BaseModel, field_validator

from ..models.product import ProductType


class ProductBase(BaseModel):
    type: ProductType
    name: str
    description: str | None = None
    price: float
    classes_count: int | None = None
    validity_days: int | None = None
    direction_limit_id: int | None = None
    is_active: bool = True

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value: object) -> ProductType:
        if isinstance(value, ProductType):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            aliases: dict[str, ProductType] = {
                ProductType.subscription.value: ProductType.subscription,
                ProductType.single.value: ProductType.single,
                "abon": ProductType.subscription,
            }
            if normalized in aliases:
                return aliases[normalized]
        raise ValueError("Invalid product type")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    type: ProductType | None = None
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
