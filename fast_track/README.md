# Fast Track

TypeScript package for the Fast Track Bot: **guardrails** that judge a PR and
produce a machine-readable verdict, and a **bot** that acts on that verdict. Two
thin GitHub workflows launch it.

Runs via [`tsx`](https://tsx.is/) — no build step, no compiled artifact.

> **Status:** the judging half is live. The verdict contract, the guardrail
> framework (context types, an always-pass dummy guardrail, the registry +
> selector), the runner, and both context providers (local `git` and CI `API`)
> are in place with unit tests. `make run-guardrails` judges your branch's
> committed changes locally; the **Fast Track Checks** workflow
> ([`.github/workflows/fast_track_checks.yml`](../.github/workflows/fast_track_checks.yml))
> runs the guardrails on every non-draft PR with a read-only token and uploads
> the verdict as an artifact. The bot and its workflow — the acting half — land
> in subsequent PRs.

## The two components

- **Fast Track Checks** (this workflow, read-only): runs the guardrails in PR
  context via `npm run checks` and writes `verdict.json`. Holds no credential
  that can approve. Not a required status check.
- **Fast Track Bot** (later PR, base-repo context): reads the verdict artifact
  and approves / dismisses / comments with a GitHub App token.

## Local commands

```bash
make install          # npm ci with the pinned Node (.nvmrc)
make static-checks    # prettier + eslint + tsc --noEmit
make test             # vitest
make format           # prettier --write + eslint --fix
make run-guardrails   # run the guardrails against the current branch
make list-guardrails  # print the guardrail registry
```

`make run-guardrails` diffs `BASE_REF...HEAD` (three-dot, matching GitHub's
Files-changed view; default `origin/main`) and exits non-zero on a fail. It sees
**committed** changes only, so commit before running.

```bash
# Run only selected guardrails (comma-separated; an unknown name errors out).
GUARDRAILS=dummy make run-guardrails

# Diff against a different base (e.g. the parent branch of a stacked PR).
BASE_REF=origin/develop make run-guardrails
```

## Toolchain

- **Node** floor enforced by `engine-strict` + `engines` (`>=24`); the exact
  version (`24.13.1`) is pinned in [`.nvmrc`](.nvmrc) for `nvm`/`make` users.
- **TypeScript** in `--noEmit` mode — type-checking only; code runs via `tsx`.
- **ESLint 9** flat config + `typescript-eslint`, with `eslint-config-prettier`
  so formatting is Prettier's job alone.
- **Prettier** for formatting.
- **Vitest** for unit tests (`*.test.ts` next to their source).
