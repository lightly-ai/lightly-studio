"""Lightly Studio Exceptions types."""


class NotFoundError(Exception):
    """Exception signaling that a requested resource has not been found."""


class TagNotFoundError(Exception):
    """Exception signaling that a tag has not been found."""


class InvalidTagError(ValueError):
    """Exception signaling that a tag is invalid for the requested operation."""


class InvalidSamplingRequestError(ValueError):
    """Exception signaling that sampling request parameters are inconsistent."""


class QueryExprError(Exception):
    """Exception raised when a query expression cannot be translated."""
