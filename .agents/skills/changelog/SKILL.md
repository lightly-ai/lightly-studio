---
name: changelog
description: Read before adding or editing an entry in CHANGELOG.md or lightly_studio_serve/CHANGELOG.md. Says what an entry contains, how long it is, and which prefixes to use.
---

# Changelog Entries

The changelog becomes the release notes. Write each entry for a person who uses
LightlyStudio, not for a person who reviews the code.

## Rules

- Say what the user can now do, or what changed for them. One change per entry.
- Use one or two short sentences.
- Do not describe how the code works: no internal functions, precedence rules, retries,
  or database tables. Name a public API only when users call or implement it.
- Start a change to the Python SDK with `Python SDK:`.
- Start a change that breaks existing code or data with `BREAKING:`. Add the one step
  that users must do.
- Do not add ticket ids (`LIG-1234`) or PR numbers.
- Put the entry under the correct heading of `## [Unreleased]`: Added, Changed,
  Deprecated, Removed, Fixed, or Security.

## Example

Bad:

> Python SDK: New annotation crops and video frames are embedded in the embedding space
> of their parent collection, also in a later process with no registered embedder. A
> registered embedder for crops or frames still takes priority. If no embedder is
> available for the parent's space, embedding is skipped with a warning and a later run
> retries.

Good:

> Python SDK: Crops and frames get embedded with a remote embedder automatically when a
> compatible remote embedder was used previously.
