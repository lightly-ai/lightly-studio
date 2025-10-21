# Python coding guidelines

## General guidelines

When importing, import classes directly. For functions, import the containing module and call the function using dot notation.

Inside each file, put public classes then public functions, then private classes, and finally private functions.

For todos, use a format `# TODO({Name}, {month}/{year}): {full_sentence_comment}`, e.g. `# TODO(Michal, 08/2023): Address in the next PR.`.

If using docstrings, use the google style guide and triple quotes. Use `Args:` and `Returns:` sections. Don't repeat the type in the description.
Any example:
```python
def foo(bar: int) -> str:
    """Converts an integer to a string.

    Args:
        bar: The bar to convert.

    Returns:
        The converted bar.
    """
    return str(bar)
```

For comments outside of docstrings, use full sentences and proper punctuation.
E.g. `# This is a comment.` instead of `# this is a comment`.

Avoid using `assert` outside of tests.

Always use keyword arguments when calling functions, except for single-argument functions.

Don't care about formatting, we use ruff for that.

## Typing

Always use type hints, such that mypy passes.

Use newer syntax e.g. `list[int | None]` instead of `List[Optional[int]]`. When needing them, add `from __future__ import annotations` at the top of the file.

Use abstract inputs and concrete outputs. See this example:
```python
def add_suffix_to_list(lst: Sequence[str], suffix: str) -> list[str]:
    return [x + suffix for x in lst]
```

Use Sequence and Mapping instead of list and dict for immutable types. Import them from `collections.abc`.

Be specific when ignoring type errors, e.g. `# type: ignore[no-untyped-call]` instead of `# type: ignore`.

## Testing

Always use pytest, never unittest.

When testing a class named `MyClass`, put all tests under a class named `TestMyClass`.

When testing a function or method, name it `test_{method_name_with_underscores}`.
E.g. the test for `_internal_function` is named `test__internal_function`.
E.g. the test for `MyClass.my_method` is named `TestMyClass.test_my_method`.

When testing a special case of a function or method append a `__{special_case}` to the test name.
E.g. the test for the function `compute_mean(arr: list[float])` for the empty array case
should be named `test_compute_mean__empty_array`.
