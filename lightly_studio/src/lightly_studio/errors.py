"""Lightly Studio Exceptions types."""


class TagNotFoundError(Exception):
    """Exception signaling that a tag has not been found."""


class QueryExprError(Exception):
    """Exception raised when a query expression cannot be translated."""


class MetadataKeyNotFoundError(Exception):
    """Exception signaling that a metadata key is absent from a collection."""


class UnsupportedMetadataTypeError(Exception):
    """Exception signaling that a metadata type is not supported by an operation."""
