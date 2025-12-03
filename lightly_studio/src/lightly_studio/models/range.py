"""Models representing numeric ranges."""

from pydantic import BaseModel


class FloatRange(BaseModel):
    """Defines a range of floating-point values."""

    min: float
    max: float


class IntRange(BaseModel):
    """Defines a range of integer-point values."""

    min: int
    max: int
