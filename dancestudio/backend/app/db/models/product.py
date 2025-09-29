from enum import Enum as PyEnum
from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..session import Base


class ProductType(str, PyEnum):
    subscription = "subscription"
    single = "single"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[ProductType] = mapped_column(Enum(ProductType), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    classes_count: Mapped[int | None] = mapped_column(Integer)
    validity_days: Mapped[int | None] = mapped_column(Integer)
    direction_limit_id: Mapped[int | None] = mapped_column(ForeignKey("directions.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    direction = relationship("Direction")
    subscriptions = relationship("Subscription", back_populates="product")
