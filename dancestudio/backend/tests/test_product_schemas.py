import pytest
from pydantic import ValidationError

from app.db.models.product import ProductType
from app.db.schemas.product import ProductCreate


def test_product_create_accepts_abon_alias() -> None:
    product = ProductCreate(type="abon", name="Abon", price=100.0)

    assert product.type is ProductType.subscription
    assert product.model_dump()["type"] == ProductType.subscription


def test_product_create_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(type="unknown", name="Test", price=10.0)
