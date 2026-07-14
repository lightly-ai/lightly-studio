# Design docs

Internal engineering documentation: one document per substantial feature or
architectural change, written alongside the implementing PR. Unlike the
user-facing product docs (`lightly_studio/docs`), these capture *why* the code
looks the way it does — the problems encountered, the decisions made, the
alternatives rejected, and the known limitations — so reviewers can comment on
reasoning rather than reverse-engineer it, and future readers get the context
git blame can't give.

Conventions:

- One markdown file per feature, kebab-case, e.g. `numeric-metadata-histograms.md`.
- Written (or at least drafted) in the same PR as the implementation, so review
  comments can anchor to it.
- Number the decisions/issues within a doc so they can be referenced directly
  in review threads.
- Keep them honest: document what didn't work and what was deliberately left
  out, not just the happy path.

For single, narrowly-scoped architectural decisions, the ADR format
(<https://adr.github.io/>) is a reasonable alternative; adopt `docs/adr/` if
that need arises.
