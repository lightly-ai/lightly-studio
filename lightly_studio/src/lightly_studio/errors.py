"""Lightly Studio Exceptions types."""


class TagNotFoundError(Exception):
    """Exception signaling that a tag has not been found."""


class QueryExprError(Exception):
    """Exception raised when a query expression cannot be translated."""


class SortExprError(Exception):
    """Exception raised when a sort expression cannot be translated."""
