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

- Add less than 200 lines of core logic. Tests, deleted lines, and generated files do not count.
- The Fast Track guardrail measures this approximately. Run it on the committed changes before
  each push: `cd fast_track && GUARDRAILS=diff-size make run-guardrails`. For a stacked PR, add
  `BASE_REF=<parent branch>`.
- The limit is a target, not a hard rule. Split a larger change into stacked PRs if each part is
  reviewable alone. Do not split one coherent change only to fit; a larger PR gets a human review.

## One Purpose

- A PR does one thing. Do not mix unrelated changes.
- Put a refactor in a different PR from a behavior change. A small cleanup next to the main
  change is acceptable.
- Add tests for new behavior in the same PR.

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

## Did you update [CHANGELOG.md](../CHANGELOG.md)?

- [x] Yes
- [ ] Not needed (internal change)
```

## Before You Open the PR

- Run the checks in the Validation section of `AGENTS.md` for each package that you changed. For
  `lightly_studio_serve` and `fast_track`, run `make static-checks` and `make test` in the package
  folder.
- Open the PR as a draft while the work is not complete. The guardrails and the E2E tests do
  not run on a draft. To run the E2E tests on a draft, add the `run-e2e` label and push again. The
  `run-e2e-merge-queue` label runs what the merge queue runs: these tests plus Postgres and Groups.
- Propose the reviewer who knows the changed files best, from `git log` of those files. Use the
  same reviewer for each PR of a stack.

## Exceptions

Dependency upgrades, mechanical codemods, large test updates, migrations, and generated files can
be larger than the limit. For these PRs:

- Say in the description why the PR is large.
- Keep mechanical changes and logic changes in different commits or PRs.
- Name the risk areas.
