"""Parameter for operators for LightlyStudio plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast

T = TypeVar("T")


@dataclass
class BaseParameter(ABC):
    """Base parameter definition shared across operator parameters."""

    name: str
    description: str = ""
    default: Any = None
    required: bool = True
    param_type: str | None = None

    def __post_init__(self) -> None:
        """Run value validation once the dataclass is initialized."""
        if self.default is not None:
            self.default = self._validate(self.default)

    @abstractmethod
    def _validate(self, value: Any) -> Any:
        """Validate the parameter value."""


class BuiltinParameter(BaseParameter, Generic[T]):
    """Represents a built-in operator parameter."""

    def __post_init__(self) -> None:
        """Set up type information and validate default value."""
        if not hasattr(self, "_parameter_type") or self._parameter_type is None:
            raise NotImplementedError("Subclasses must define _parameter_type class attribute")
        self._type = self._parameter_type
        self.param_type = self._parameter_type.__name__
        super().__post_init__()

    def _validate(self, value: T) -> T:
        if isinstance(value, self._type):
            return cast(T, value)
        raise TypeError(f"Expected value of type '{self._type.__name__}' but got {type(value)}'")


class IntParameter(BuiltinParameter[int]):
    """Represents an integer operator parameter."""

    _parameter_type = int


class FloatParameter(BuiltinParameter[float]):
    """Represents a float operator parameter."""

    _parameter_type = float


class BoolParameter(BuiltinParameter[bool]):
    """Represents a boolean operator parameter."""

    _parameter_type = bool


class StringParameter(BuiltinParameter[str]):
    """Represents a string operator parameter."""

    _parameter_type = str
