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

Exceptions from the guidelines:
- We allow direct function import from `typing` in Python

## File layout

- Put important functions at the top
    - Especially, put public functions before private ones
    - Classes should come before global functions, if they are present
- Rationale: The file should be easy to understand when read top-to-bottom. Important information therefore should be towards the top of the file.

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

Prefer properly formatted comments with a leading capital and punctuation. Final full stop may be omitted for a single sentence.

```python
# This is a proper comment. It spans multiple sentences.
...

# Single sentences can have the final full stop omitted
...

# we don't do this <-
...
```

## Assertions

- Avoid using assertions:
    - Don’t use assertions for user errors, raise an exception instead.
    - Assertions should never fail. If they do it is a bad internal error.
    - Don’t assert that a variable follows its typehint.

They can be used:

- for invariants that are easy to check locally, like a minimum length
- for typing (e.g. non-nullity)
- To document what we expect a particular value to be. Here, expect means that there would need to be some logical error somewhere for the value to be different.
- in a private function when the calling code makes the check

It’s ok to not test assertions as they’re not the intended behavior of a function.

Example:

```python
def get_metrics(values: list[float]) -> Something:
    ...
    if len(values) < 2:
        std = 0 # Or an Error is raised.
    else:
        std = _get_std(values)
    ...

def _get_std(sequence: Sequence[float]) -> float:
    """Gets the standard deviation of a sequence

    Args:
        sequence:
            The sequence to get the std of.
            Must have a length >= 2.

    Returns:
            The standard deviation of a sequence.

    """

    assert len(sequence) >= 2
    return np.std(sequence)
```

## Positional vs. Keyword Arguments

In general: Call functions using keyword arguments.

```python
def fn(hello: str, person: str) -> None:
    ...

fn(hello="Grüezi", person="Bob")
```

The exception of using positional arguments is allowed for

- functions with only 1 argument, e.g. `def is_palindrome(a: str)`
- functions where confusing the arguments does not matter, e.g `def add(a: int, b: int)`
- if the keyword arguments are not known, e.g. because the function is only given through typing: `transform: Callable[[Tensor], Tensor]` must be called as `transformed = transform(tensor)`
- for common standard library functions like e.g. `print`, `math.exp`

## `__init__.py` files

Don't put logic in `__init__.py` files. They should be preferrably empty, or just expose submodule symbols for convenience.

Exceptions may apply occasionally. Such logic should be accompanied by a comment explaining why it is done.

## Docstrings

### Class-level Docstrings

Document the functionality of the class and its **public attributes** if they are not already
documented on the class level.

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

### Constructor-level Docstrings

Should have its own arguments section and a brief sentence describing the functionality. Don’t write `Constructor of the SampleClass` as the description, this is not helpful.

```python
    def __init__(self, likes_spam: bool = False) -> None:
        """Initializes the instance based on spam preference.

        Args:
            likes_spam: Defines if instance exhibits this preference.
        """
        self.likes_spam = likes_spam
        self.eggs = 0
```

If **public attributes** and **constructor arguments** match exactly, prefer using Dataclasses over writing your own constructor and constructor docstring.

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
        self.likes_spam = likes_spam
        self.eggs = 0
```

# Typing

All our code must be typed.

- Prefer Python 3.10+ syntax for built-ins
    - Good: `lst: list[int]`, bad: `lst: typing.List[int]`
    - Good: `path: str | None`, bad: `path: typing.Optional[str]`
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
- Use pytest mocking

### Tests must be easy to check by hand

- Because tests are not tested
- Keep tests small. Split larger tests that check multiple cases.
- Prefer writing out test inputs instead of generating them

### Tests must use pytest (NOT unittest)

- Pytest it the better library
- If you import from unittest, it is wrong. Replace by the corresponding pytest feature instead.

## Naming

We use the following naming conventions for tests. Tests are in a folder structure parallel
to `src/{package_name}`.

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
