# Fast Track

TypeScript package for the Fast Track Bot: **guardrails** that judge a PR and
produce a machine-readable verdict, and a **bot** that acts on that verdict. Two
thin GitHub workflows will launch it (added in later PRs).

Runs via [`tsx`](https://tsx.is/) — no build step, no compiled artifact.

> **Status:** early scaffolding. The verdict contract, the guardrail framework
> (context types, an always-pass dummy guardrail, the registry + selector), the
> runner, and the local git-backed context provider are in place with unit
> tests — `make check` runs the guardrails against your working tree. The API
> context provider, the bot, and the two workflows land in subsequent,
> independently reviewable PRs.

## Local commands

```bash
make install          # npm ci with the pinned Node (.nvmrc)
make static-checks    # prettier + eslint + tsc --noEmit
make test             # vitest
make format           # prettier --write + eslint --fix
make run-guardrails   # run the guardrails against the working tree
make list-guardrails  # print the guardrail registry
```

`make run-guardrails` diffs `BASE_REF...HEAD` (default `BASE_REF=origin/main`,
three-dot to match GitHub's Files-changed view) and prints a per-guardrail
verdict, exiting non-zero on a fail. `GUARDRAILS=a,b` runs only a named subset.

## Toolchain

- **Node** floor enforced by `engine-strict` + `engines` (`>=24`); the exact
  version (`24.13.1`) is pinned in [`.nvmrc`](.nvmrc) for `nvm`/`make` users.
- **TypeScript** in `--noEmit` mode — type-checking only; code runs via `tsx`.
- **ESLint 9** flat config + `typescript-eslint`, with `eslint-config-prettier`
  so formatting is Prettier's job alone.
- **Prettier** for formatting.
- **Vitest** for unit tests (`*.test.ts` next to their source).
