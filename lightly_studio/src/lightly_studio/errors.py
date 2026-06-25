"""Lightly Studio Exceptions types."""


class TagNotFoundError(Exception):
    """Exception signaling that a tag has not been found."""


class QueryExprError(Exception):
    """Exception raised when a query expression cannot be translated."""


class AllInputFilesFailedError(Exception):
    """Exception raised when every attempted input file failed to be added.

    This signals a likely wrong path or real bug rather than a few bad files, and is
    distinct from the case where no file was attempted because all were already present.
    """
