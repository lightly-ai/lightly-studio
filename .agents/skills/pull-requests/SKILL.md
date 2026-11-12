---
name: pull-requests
description: Read when opening a pull request, writing a PR title or description, splitting work into PRs, or deciding whether a change is too large to review. Covers the title format, the Fast Track size limit and how to measure it, the one-purpose-per-PR rule, the description template, the changelog checkbox, and the exceptions for dependency bumps, codemods, migrations, and generated files.
---

# Pull Request Guidelines

A reviewer must be able to review a PR in less than 15 minutes.

## Title

Use a Conventional Commits prefix and an imperative sentence:

- `feat:` for new behavior, `fix:` for a bug fix.
- `refactor:`, `test:`, `docs:`, `chore:` for changes that users do not see.

```
feat: store per-class average precision of object-detection runs
fix: keep the selected tag when the grid reloads
```

## Size

- The Fast Track guardrail fails a PR that adds more than 215 lines. Deleted lines do not count.
- Aim for less than 100 added lines of core logic.
- The guardrail does not count `uv.lock`, the `package-lock.json` files,
  `lightly_studio/tests/benchmarks/`, and `lightly_studio/src/lightly_studio/vendor/`.
- Measure before each push: `git diff --numstat $(git merge-base origin/main HEAD)`.
- The limit is a target, not a hard rule. Split a larger change into stacked PRs if each part is
  reviewable alone. Do not split one coherent change only to fit; a larger PR gets a human review.

## One Purpose

- A PR does one thing. Do not mix unrelated changes.
- Put a refactor in a different PR from a behavior change. A small cleanup next to the main
  change is acceptable.
- Add tests for new behavior in the same PR. Move them to a second PR only if the first PR
  becomes too large.

## Description

- Use the sections of `.github/pull_request_template.md`. Do not add other sections.
- Keep the description short: a few bullets that give the problem and the solution. Write them
  for a reader who does not know the code.
- Write in ASD-STE100 Simplified Technical English: short sentences, active voice, present tense.
- Tick one changelog box. A change that users see needs an entry; see the changelog skill.
- Add screenshots or a recording for a GUI change.

```markdown
## What has changed and why?

- The grid lost the selected tag after a reload.
- The tag selection now comes from the URL, not from component state.

## How has it been tested?

- Added a unit test for `useTags`.
- Reloaded the grid with a selected tag in the GUI.
```

## Before You Open the PR

- Run the checks in the Validation section of `AGENTS.md` for each package that you changed.
- Open the PR as a draft while the work is not complete. The guardrails do not run on a draft.
- Propose the reviewer who knows the changed files best, from `git log` of those files. Use the
  same reviewer for each PR of a stack.

## Exceptions

Dependency upgrades, mechanical codemods, large test updates, migrations, and generated files can
be larger than the limit. For these PRs:

- Say in the description why the PR is large.
- Keep mechanical changes and logic changes in different commits or PRs.
- Name the risk areas.
