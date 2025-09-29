from pydantic import BaseModel


class DirectionBase(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True


class DirectionCreate(DirectionBase):
    pass


class DirectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class Direction(DirectionBase):
    id: int

    class Config:
        from_attributes = True
