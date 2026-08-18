"""Lightly Studio Exceptions types."""


class NotFoundError(Exception):
    """Exception signaling that a requested resource has not been found."""


class TagNotFoundError(Exception):
    """Exception signaling that a tag has not been found."""


class QueryExprError(Exception):
    """Exception raised when a query expression cannot be translated."""


class DuplicateCollectionNameError(Exception):
    """Exception signaling that more than one collection matches a name lookup.

    This indicates a data integrity issue: collection names are expected to be
    unique per parent (root collections included), so a lookup should never
    match more than one row.
    """
