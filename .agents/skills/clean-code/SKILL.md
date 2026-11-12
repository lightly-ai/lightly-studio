---
name: clean-code
description: Read before writing, refactoring, or reviewing code in any language in this repository. Gives the checkable clean-code rules for names, function shape, nesting, boolean flags, side effects, file size, dead code, duplication, error handling, lint suppressions, and comments.
---

# Clean Code

Code must be self-descriptive. A reader understands it from the names and the structure, without
comments. The language guides add the rules for Python, the backend, and the frontend.

## Names

- A name states what the value is or what the function does. Do not use `data`, `info`, `tmp`,
  `handle`, or `process` alone.
- Use the term from the glossary skill for a domain noun.
- Give a complex expression a name. Do not write it inline.

```python
# Bad
if sample.width * sample.height > 1024 * 1024 and not sample.tags:
    ...

# Good
is_large = sample.width * sample.height > MAX_PIXELS
is_untagged = not sample.tags
if is_large and is_untagged:
    ...
```

## Functions

- A function does one thing. You can describe it without the word "and".
- A function has one level of abstraction. It calls helpers or it does the detail work, not both.
- Use guard clauses. Keep the nesting depth at 2 levels or less.
- Do not add a boolean argument that selects between two behaviors. Write two functions.
- A function that returns a value does not change its inputs or global state.
- A function or component accepts only the data that it uses, not the full object.
- Combine small units. Do not build a deep class hierarchy.

```python
# Bad
def export(samples, as_json):
    if samples:
        for sample in samples:
            if sample.is_valid:
                ...

# Good
def export_json(samples):
    for sample in samples:
        if not sample.is_valid:
            continue
        ...
```

## Size

- The linters check the complexity. Do not add `noqa` or `eslint-disable` to pass the check.
  Split the code.
- If a function is longer than approximately 20 lines, make sure that it still does one thing.
- Keep a file under 400 lines. The frontend guide has a lower limit for components.

## Dead Code and Duplication

- Delete dead code and commented-out code.
- Extract duplicated code at the third copy, not before.

## Errors

- Do not catch an exception that you do not handle. Do not write a bare `except Exception` or an
  empty `catch`.

## Comments

- The code says what it does. A comment gives a reason that the code cannot show.
- If a comment says what the code does, rename or extract until the comment is not necessary.
- Keep an inline comment short, one line if possible. A longer comment is acceptable for inner
  logic that names cannot explain. The contract of the function goes in the docstring.
- Describe the current state, not the change.
- Write comments, docstrings, and error messages in ASD-STE100 Simplified Technical English:
  short sentences, active voice, present tense, and one meaning for each word.

```python
# Bad: Says what the code does.
# Loop over the samples and skip the invalid ones.

# Good: Gives the reason.
# The embedding model accepts at most 64 images in one batch.
```
