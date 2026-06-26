"""Lightly Studio Exceptions types."""


class TagNotFoundError(Exception):
    """Exception signaling that a tag has not been found."""


class QueryExprError(Exception):
    """Exception raised when a query expression cannot be translated."""


class InputFileError(Exception):
    """Base exception for a bad input file that is tolerated per-item.

    Raise a subclass at the I/O boundary that has the context to classify why a
    file failed. Pipeline steps route file operations through
    `FileOutcomeReport.track`, which records the matching outcome and continues
    the loop instead of crashing the whole run.
    """


class MissingInputFileError(InputFileError):
    """Exception signaling that an input file path does not resolve.

    Detect this proactively with `fs.exists()` rather than relying on
    `FileNotFoundError`, which is unreliable across fsspec backends and is a
    subclass of `OSError`.
    """


class BrokenInputFileError(InputFileError):
    """Exception signaling that an input file is present but unreadable/undecodable.

    Translate decode/read failures into this at the boundary that has the
    context, e.g. `raise BrokenInputFileError(path) from exc`.
    """


class AllInputFilesFailedError(Exception):
    """Exception raised when every attempted input file failed.

    Distinguishes a run where every file was broken or missing from one where
    individual files were tolerated. Files that were already present are not
    counted as attempted, so a run that only skips already-present files does
    not raise this.
    """
