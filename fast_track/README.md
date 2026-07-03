# Fast Track

TypeScript package for the Fast Track Bot: **guardrails** that judge a PR and
produce a machine-readable verdict, and a **bot** that acts on that verdict. Two
thin GitHub workflows will launch it (added in later PRs).

Runs via [`tsx`](https://tsx.is/) — no build step, no compiled artifact.

> **Status:** early scaffolding. The verdict contract, the guardrail framework
> (context types, an always-pass dummy guardrail, the registry + selector), the
> runner, the local git-backed context provider, and the API-backed context
> provider are in place with unit tests — `make run-guardrails` runs the
> guardrails against your branch's committed changes. The bot and the two
> workflows land in subsequent, independently reviewable PRs.

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
