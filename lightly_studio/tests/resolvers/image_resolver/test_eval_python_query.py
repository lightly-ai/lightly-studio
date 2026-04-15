import pytest

from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.resolvers.image_resolver.get_all_by_collection_id import (
    _eval_python_query,
)


# ---------------------------------------------------------------------------
# Valid expressions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "ImageSampleField.width > 1920",
        "ImageSampleField.width >= 100",
        "ImageSampleField.width < 100",
        "ImageSampleField.width <= 100",
        "ImageSampleField.width == 1920",
        "ImageSampleField.width != 1920",
        "ImageSampleField.width > -1",
        'ImageSampleField.file_name == "cat.png"',
        'ImageSampleField.tags.contains("cat")',
        "AND(ImageSampleField.width > 100, ImageSampleField.height > 100)",
        "OR(ImageSampleField.width > 100, ImageSampleField.height > 100)",
        "NOT(ImageSampleField.width > 100)",
        'AND(ImageSampleField.width > 100, ImageSampleField.tags.contains("cat"))',
    ],
)
def test_valid_query_returns_match_expression(query: str) -> None:
    result = _eval_python_query(query)
    assert isinstance(result, MatchExpression)


# ---------------------------------------------------------------------------
# Disallowed constructs — must raise ValueError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        # Import statements
        "__import__('os').system('id')",
        # Accessing builtins via dunder traversal
        "().__class__.__base__.__subclasses__()",
        # Dunder attribute access
        "ImageSampleField.__class__",
        "ImageSampleField.width.__class__",
        # Unknown top-level name
        "os.path.exists('/etc/passwd')",
        "open('/etc/passwd')",
        "UnknownField.width > 1",
        # Unsupported node types
        "[x for x in []]",  # ListComp
        "{1: 2}",  # Dict
        "lambda x: x",  # Lambda
        # Chained comparison
        "1 < ImageSampleField.width < 1920",
        # Keyword arguments
        "AND(ImageSampleField.width > 1, key=True)",
        # Unsupported constant type
        "ImageSampleField.width == b'bytes'",
    ],
)
def test_disallowed_query_raises_value_error(query: str) -> None:
    with pytest.raises(ValueError):
        _eval_python_query(query)


def test_syntax_error_raises_value_error() -> None:
    with pytest.raises(ValueError, match="syntax"):
        _eval_python_query("ImageSampleField.width >")


def test_non_match_expression_raises_value_error() -> None:
    # Valid Python, valid AST, but result is not a MatchExpression.
    with pytest.raises(ValueError, match="MatchExpression"):
        _eval_python_query("ImageSampleField.width")
