"""Parameter for operators for LightlyStudio plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseParameter(ABC):
    """Base parameter definition shared across operator parameters."""

    __slots__ = ("default", "description", "name", "param_type", "required")

    @abstractmethod
    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        default: Any = None,
        required: bool = True,
    ) -> None:
        """Initialize the parameter."""
        self.name = name
        self.description = description
        self.required = required
        self.default = self._validate(default) if default is not None else None

    def to_dict(self) -> dict[str, Any]:
        """Convert parameter to dictionary representation."""
        return {
            "name": self.name,
            "type": self.param_type,
            "description": self.description,
            "default": self.default,
            "required": self.required,
        }

    @staticmethod
    @abstractmethod
    def _validate(value: Any) -> Any:
        """Validate the parameter value."""


class IntParameter(BaseParameter):
    """Represents an integer operator parameter."""

    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        default: int | None = None,
        required: bool = True,
    ) -> None:
        """Initialize the parameter."""
        super().__init__(name=name, description=description, default=default, required=required)
        self.param_type = "int"

    @staticmethod
    def _validate(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("Expected value of type 'int'")
        return value


class FloatParameter(BaseParameter):
    """Represents a float operator parameter."""

    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        default: float | None = None,
        required: bool = True,
    ) -> None:
        """Initialize the parameter."""
        super().__init__(name=name, description=description, default=default, required=required)
        self.param_type = "float"

    @staticmethod
    def _validate(value: Any) -> float:
        if isinstance(value, bool):
            raise TypeError("Expected value of type 'float'")
        if isinstance(value, (int, float)):
            return float(value)
        raise TypeError("Expected value of type 'float'")


class BoolParameter(BaseParameter):
    """Represents a boolean operator parameter."""

    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        default: bool | None = None,
        required: bool = True,
    ) -> None:
        """Initialize the parameter."""
        super().__init__(name=name, description=description, default=default, required=required)
        self.param_type = "bool"

    @staticmethod
    def _validate(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        raise TypeError("Expected value of type 'bool'")


class StringParameter(BaseParameter):
    """Represents a string operator parameter."""

    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        default: str | None = None,
        required: bool = True,
    ) -> None:
        """Initialize the parameter."""
        super().__init__(name=name, description=description, default=default, required=required)
        self.param_type = "str"

    @staticmethod
    def _validate(value: Any) -> str:
        if isinstance(value, str):
            return value
        raise TypeError("Expected value of type 'str'")
