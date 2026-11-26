---
name: clean-code
description: Read before writing, refactoring, or reviewing code in any language in this repository. Gives the checkable clean-code rules for consistency, names, constants, function shape, nesting, boolean flags, side effects, file size, dead code, duplication, error handling, root causes, lint suppressions, and comments.
---

# Clean Code

Code must be self-descriptive. A reader understands it from the names and the structure, without
comments. The language guides add the rules for Python, the backend, and the frontend.

## Consistency

- Look at how the nearby code does a similar task. Use the same pattern if it is a good design.
- Old code is not always correct. Do not copy a pattern that breaks a rule in this skill or in the
  language guides. Tell the user about the problem and propose a better design.
- Do not refactor the old code in the same change. Propose the refactor as a separate PR.
- Do not add a second pattern for the same thing without a reason. Give the reason to the user.

## Names

- A name states what the value is or what the function does. Do not use `data`, `info`, `tmp`,
  `handle`, or `process` alone.
- Use the term from the glossary skill for a domain noun.
- Give a complex expression a name. Do not write it inline.
- Give a literal number a name: use a constant. `0`, `1`, and `-1` are acceptable inline.
- Do not write a double negative. Write `if is_valid`, not `if not is_invalid`.
- Keep synthetic values distinct from user-defined values. Use an explicit marker for branching
  or separate namespaces for IDs. Reserve a raw value only if validation excludes it from user
  input.

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

- Do not add `noqa`, `type: ignore`, or `eslint-disable` to pass a lint or type check. Fix the
  code; for a complexity error, split the function. A suppression is acceptable only for an
  exception that a language guide lists.
- If a function is longer than approximately 20 lines, make sure that it still does one thing.
- Keep a file under 400 lines. The frontend guide has a lower limit for components.

## Dead Code and Duplication

- Delete dead code and commented-out code.
- Extract duplicated code at the third copy, not before.

## Errors

- Do not catch an exception that you do not handle. Do not write a bare `except Exception` or an
  empty `catch`.
- Fix the cause of a bug, not the symptom. Do not add a special case or a retry that hides the
  failure.

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
