---
name: python-guide
description: Read before writing or reviewing any Python code in this repository. Covers import style (modules for functions, direct for classes), file layout ordering (private functions at the bottom), protocols vs ABCs, TODO and comment format, no assertions outside tests, preference for keyword arguments, docstrings including tensor shapes, typing, and pytest conventions.
---

# Python Code Guidelines

No rules here are hard, but they are strong recommendations. The golden rule is to make the code easy to understand and difficult to break.

We use the `ruff` code formatter and `mypy` type checker with custom settings. You don't need to check rules enforced by these tools like e.g. line length.

# Code Style

## Imports

- For functions, import the containing module and call the function using dot notation
- Import classes directly
- Rationale: Using dot notation makes it obvious in the code when a function is external and leads to a more succinct import code. Classes are an exception, they are often used as type hints so less verbosity is preferred.

```python
from mypackage import mymodule
from mypackage.mymodule import MyClass

mymodule.foo()
c = MyClass()
```

Put all imports at the top of the file. Do not import inside a function, a method, or a class.
Ruff rule `PLC0415` checks this. Do not add `# noqa: PLC0415` to break an import cycle or to make
a module load faster; move the shared code to a module that both sides can import.

```python
# Bad
def export(samples: Sequence[Sample]) -> None:
    from mypackage import writer

    writer.write(samples)
```

Exceptions from the guidelines:
- An import inside a function is allowed only for an optional dependency that is possibly not
  installed, for example `pgvector`. Add `# noqa: PLC0415`.
- We allow direct function import from `typing`, `dataclasses`, `abc`, `sqlmodel`, `sqlalchemy`
- In tests, we allow direct function import from `tests.helpers_resolvers`,
  `tests.resolvers.video.helpers`, and `tests.resolvers.evaluation_sample_metric_resolver.helpers`

## File layout

- Put important functions at the top
    - Especially, put public functions before private ones
    - Classes should come before global functions
- Rationale: The file should be easy to understand when read top-to-bottom. Important information should be towards the top of the file.

```python
from x import y

class MyClass:
    def __init__(self):
        ...

    def foo(self):
        ...

    def _helper_method(self):
        ...

def bar(...):
    ...

def _helper_func(...):
    ...
```

## Protocols vs ABCs

- It’s ok to use ABCs when appropriate (consider nominal vs structural subtyping).
- Prefer composition over inheritance.
    - Inheritance can introduce bi-directional flow of information between parent and child class.
    - Higher flexibility

## TODOs

Use the following format: `# TODO({name}, {mm}/{yyyy}): Blah blah`

```python
# TODO(Michal, 08/2023): Blah blah
```

## Comments

Code must be self-descriptive. Write a comment only for a reason that the code cannot show.
Keep an inline comment to one line and put more detail in the docstring.

Use ASD-STE100 Simplified Technical English, avoid bloat. Describe the current state, not the change. Prefer properly formatted comments with a leading capital and punctuation. Final full stop may be omitted for a single sentence.

```python
# This is a proper comment. It spans multiple sentences.
...

# Single sentences can have the final full stop omitted
...

# we don't do this <-
...
```

## Assertions

Do not use `assert` outside tests. Python removes assertions with the `-O` flag, and an
`AssertionError` does not tell the caller what to do.

- Raise an exception for a condition that can fail, also for an internal error.
- To narrow a type for mypy, check the value and raise.
- Do not check that a variable follows its type hint.

```python
# Bad
assert sample is not None
assert len(values) >= 2

# Good
if sample is None:
    raise ValueError(f"Sample {sample_id} does not exist.")
if len(values) < 2:
    raise ValueError("At least 2 values are necessary.")
```

## Positional vs. Keyword Arguments

Call functions using keyword arguments, whether or not the arguments are declared keyword-only with `*`. Do not declare arguments as keyword-only with `*` in our code.

```python
def fn(hello: str, person: str) -> None:
    ...

fn(hello="Grüezi", person="Bob")
```

The exception of using positional arguments is allowed for

- if the keyword arguments are not known, e.g. because the function is only given through typing: `transform: Callable[[Tensor], Tensor]` must be called as `transformed = transform(tensor)`
- for common standard library functions like e.g. `print`, `math.exp`, `zip`, `isinstance`, `dict.get`, etc.
- For common functions from core frameworks such as `datetime`, `pytest`, `numpy`, `pytorch`, `logging`, etc.
- For SQL ORM functions like `select`, `col`, etc.

## `__init__.py` files

Don't put logic in `__init__.py` files. They should be preferrably empty, or just expose submodule symbols for convenience.

Exceptions may apply occasionally. Such logic should be accompanied by a comment explaining why it is done.

## Docstrings

### Function and method-level Docstrings

We use Google style docstrings.

```python
def foo(bar: int) -> str:
    """Summary of function here.

    Longer function information...

    Args:
        bar: Description of the argument `bar`.

    Returns:
        Description of the return value.

    Raises:
        ValueError: Description of the error that may be raised.
    """
```

### Class-level Docstrings

Document the functionality of the class. Document each **public attribute** in the `Attributes`
section or in a docstring below the attribute, not in both.

```python
class SampleClass:
    """Summary of class here.

    Longer class information...

    Attributes:
        likes_spam: A boolean indicating if we like SPAM or not.
        eggs: An integer count of the eggs we have laid.
    """

    name: str
    """An example docstring."""

```

### Tensor Shapes in Docstrings

- The tensor shapes in the `Args` and `Returns` sections should be documented through capital letters in parentheses.
- The explanation of these letters happens above in the method/function description.
- Tensor `dtypes` must be documented unless the `dtype` is `torch.float32` which is assumed to be the default.

```python
    def forward(self, pointclouds: Tensor, index: Tensor) -> Tensor:
        """Propagates a batch of 3D point clouds through the model.
        
        B corresponds to the batch size, N is the number of points in each (padded)
        pointcloud and D is the output dimension of the extracted features.
        
        Args:
            pointclouds: Tensor of shape (B, N, 3).
            index: Binary index for the padded pointcloud of shape (B, N) of dtype
                `torch.bool`.
            
        Returns:
            Reduced point clouds of the shape (B, D).
        """
```

# Typing

All our code must be typed.

- Use Python 3.10+ syntax for built-ins. Do not use `Optional` or `Union`.
    - Good: `lst: list[int]`, bad: `lst: typing.List[int]`
    - Good: `path: str | None`, bad: `path: typing.Optional[str]`
    - Good: `value: int | str`, bad: `value: typing.Union[int, str]`
- Use built in ABCs
    - Use `Sequence` and `Mapping` for immutable `list` and `dict`
    - Import from collections.abc:
        - Good: `from collections.abc import Sequence, Mapping`
        - Bad: `from typing import Sequence, Mapping`
        - Rationale: The latter is deprecated by PEP 585
- Use abstract inputs and concrete outputs:
    - Good (note: toy example, it could accept and return Iterable in this case):
        
        ```python
        def add_suffix_to_list(lst: Sequence[str], suffix: str) -> list[str]:
            return [x + suffix for x in lst]
        ```
        
- Be specific when ignoring a type error
    - Good: `def foo(x: Any) -> None:  # type: ignore[misc]`
    - Bad: `def foo(x: Any) -> None:  # type: ignore`
    - Rationale: Ignoring all type errors might miss an error that was not intended.
        
- Torch typing
    - Type all tensors with `from torch import Tensor`
    - Note that things like `FloatTensor` and `LongTensor` should NOT be used as they are deprecated and cannot be typed by mypy.

# Testing

### Golden rule: Write code that is easy to test

- Such code indicates good design - functionality is well isolated
- Functions are easier to test than class methods
- Single responsibility functions are easy to test
- Code using dependency injection is easy to test

### Write strong signal tests

- From an information-theoretic point of view, we want to maximise `P(correct|passes)`: The probability that an implementation is correct given the test passes.
- Cover a typical case. Cover edge cases.
- A good set of tests should cover all branches.

### Use patching/mocking sparingly

- Prefer blackbox testing with real objects
- Mocking has its place though, especially for outside dependencies (e.g. db or network) or long-running subroutines
- Mocking is also suitable for “thin” methods that make many subcalls
- Spying can be an alternative to mocking

### Tests must be easy to check by hand

- Because tests are not tested
- Keep tests small. Split larger tests that check multiple cases.
- Prefer writing out test inputs instead of generating them

### A test states every value that its assertions depend on

- Put each value that decides the outcome (a dimension, a count, a space key, a limit) in one of these places:
    - the test body
    - a `pytest.mark.parametrize` decorator on the test
    - a constant of the test module
- Do not keep such a value only inside a fixture, a helper or the code under test.
- Write a relation between two values as the two values, not as a helper name such as "wider".
- Rationale: A test that hides a value assumes that the value never changes, and the reader cannot check it.

```python
# Bad: The first import stores dimension 3, the RandomEmbedder() default in patch_collection.
# The name "wider" is true only while that default is less than 4.
dataset.add_images_from_path(path=tmp_path / "first")
_register_wider_random_embedder(mocker=mocker)
with pytest.raises(ValueError, match=r"does not match"):
    dataset.add_images_from_path(path=tmp_path / "second")

# Good: The test body shows both dimensions.
_patch_registry(mocker=mocker, embedder=RandomEmbedder(dimension=3))
dataset.add_images_from_path(path=tmp_path / "first")
_patch_registry(mocker=mocker, embedder=RandomEmbedder(dimension=4))
with pytest.raises(ValueError, match=r"does not match"):
    dataset.add_images_from_path(path=tmp_path / "second")
```

### Tests must use pytest (NOT unittest)

- Don't import unittest. Pytest is more modern.
- Use MockerFixture for mocking.

```python
from pytest_mock import MockerFixture

def test_foo(mocker: MockerFixture):
    mock_bar = mocker.patch.object(mymodule, "bar", return_value=42)
    mock_bar.assert_called_once_with(...)

    mock_obj = mocker.MagicMock()
```

## Test Naming and File Structure

Tests must be located in a folder structure parallel
to `src/{package_name}` and use the following naming conventions:

```python
# src/my_package/dir/source.py

class MyClass:
    def __init__(self): ...
    def foo(self): ...
    
class _InternalClass:
    def _helper_method(self): ...

def bar(...): ...
def _helper_func(...): ...
```

```python
# tests/dir/test_source.py

class TestMyClass:
    def test_init(self): ...
    def test_init__some_special_case(self): ...
    def test_foo(self): ...
    
    def test_{method_name_underscores_stripped}{__{special_case} | ''}
    
class TestInternalClass:
    def test_helper_method(self): ...
    def test_helper_method__my_special_case(self): ...
        
def test_bar(): ...
def test_helper_func(): ...
```

Keep the order of test functions the same as the tested functions order.
