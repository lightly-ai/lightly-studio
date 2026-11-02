"""Lightly Studio Exceptions types."""


class NotFoundError(Exception):
    """Exception signaling that a requested resource has not been found."""


class TagNotFoundError(Exception):
    """Exception signaling that a tag has not been found."""


class QueryExprError(Exception):
    """Exception raised when a query expression cannot be translated."""


class UnknownImageSizeError(Exception):
    """Exception raised when a stored image has no known width or height."""


class ExportError(Exception):
    """An export cannot be written. The message says why and is shown to the user."""
