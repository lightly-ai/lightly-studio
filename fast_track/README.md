# Fast Track

TypeScript package for the Fast Track Bot: **guardrails** that judge a PR and
produce a machine-readable verdict, and a **bot** that acts on that verdict. Two
thin GitHub workflows will launch it (added in later PRs).

Runs via [`tsx`](https://tsx.is/) — no build step, no compiled artifact.

> **Status:** empty skeleton. This PR ports only the build/lint/test toolchain
> and pinned Node. There is no guardrail, bot, or workflow yet — those land in
> subsequent, independently reviewable PRs. `src/dummy.ts` is a placeholder so
> the package type-checks and has a test to run; it will be removed when real
> modules arrive.

## Local commands

```bash
make install          # npm ci with the pinned Node (.nvmrc)
make static-checks    # prettier + eslint + tsc --noEmit
make test             # vitest
make format           # prettier --write + eslint --fix
```

## Toolchain

- **Node** pinned via [`.nvmrc`](.nvmrc) (`engine-strict` enforces it).
- **TypeScript** in `--noEmit` mode — type-checking only; code runs via `tsx`.
- **ESLint 9** flat config + `typescript-eslint`, with `eslint-config-prettier`
  so formatting is Prettier's job alone.
- **Prettier** for formatting.
- **Vitest** for unit tests (`*.test.ts` next to their source).
