# Fast Track

TypeScript package for the Fast Track Bot: **guardrails** that judge a PR and
produce a machine-readable verdict, and a **bot** that acts on that verdict. Two
thin GitHub workflows launch it.

Runs via [`tsx`](https://tsx.is/) — no build step, no compiled artifact.

The **Fast Track Guardrails** workflow judges every non-draft PR with a read-only
token and uploads `verdict.json`. The **Fast Track Bot** workflow then runs the
trusted default-branch bot code with a short-lived App token. It validates the
artifact against the current PR head and base, refuses fork PRs, and idempotently
maintains one approval and one status comment. A crashed workflow or missing,
invalid, or stale verdict revokes the bot approval. Add the `no-fast-track`
label to opt out and defer to a human. Locally, `make run-guardrails` judges
committed changes.

## Trust and approval model

The guardrails CI runs from the current branch while the bot CI runs from main.
Therefore the bot code is considered trusted; guardrails code less so.

The bot approves the PR if the guardrails pass. However, the main branch protection
is set up with CODEOWNERS so that for certain paths a Lightly team member must
approve, in particular when the code touches the guardrails or CI.

The bot dismisses its past approvals only when a new bot run (after a new push)
does not pass. Therefore there is a window when the PR keeps an approval while
a newer commit has not been judged yet. This is intentional; it aligns with the
current philosophy of not dismissing stale approvals for faster development.

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
GUARDRAILS=diff-size make run-guardrails

# Diff against a different base (e.g. the parent branch of a stacked PR).
BASE_REF=origin/develop make run-guardrails
```

## Backend and frontend coverage guardrails

**What they do.** For every source file the PR touches, they compute the percentage
of _lines added_ covered by tests. Each file must be over **90%**.
The guardrails don't run tests themselves, they only read a report produced in CI.

| guardrail           | scope                                         | report                                 | env vars                                          |
| ------------------- | --------------------------------------------- | -------------------------------------- | ------------------------------------------------- |
| `backend/coverage`  | `lightly_studio/src/lightly_studio/**/*.py`   | a full-suite `coverage.py` JSON        | `BACKEND_COVERAGE_JSON`, `BACKEND_TESTS_PASSED`   |
| `frontend/coverage` | `lightly_studio_view/src/**/*.{ts,js,svelte}` | a full-suite vitest (Istanbul/v8) JSON | `FRONTEND_COVERAGE_JSON`, `FRONTEND_TESTS_PASSED` |

`*_COVERAGE_JSON` gives the path to the report. `*_TESTS_PASSED` is `false` when
the test run failed. The diff (`BASE_REF...HEAD`) gives the added line numbers per
file. The verdict for each file combines these lines with the report.

**When to expect a verdict.** A verdict appears only when the PR changes source in
scope. For the backend, these files are out of scope: tests, `conftest.py`,
`__init__.py`, and the `migrations/`, `examples/`, and `vendor/` trees. For the
frontend, test files (`.test.*`, `.spec.*`) and type declarations (`.d.ts`) are
out of scope. A PR that changes nothing in scope passes as `0 file(s) checked`.
The workflow runs each full suite on the same path filter. Therefore it skips the
expensive step for PRs that the guardrail does not judge.

Verdicts:

- no changed file in scope → pass, `0 file(s) checked`
- report present → each file judged at 90%; a file the report omits fails
- env var set but the file is missing → fail, `coverage report missing`
- `*_TESTS_PASSED=false` → fail, coverage is not judged on partial data
- **env var unset** → pass, with a loud `coverage skipped` summary. Only the
  local `make run-guardrails` path reaches this; CI always sets the var.

To exercise them locally, produce a report and point the guardrail at it:

```bash
# backend
cd lightly_studio
make build-lightly_studio_view   # conftest imports the app, so the dist must exist
make install-optional-deps       # some test modules need extras (e.g. s3fs)
make test-coverage               # writes lightly_studio/coverage.json
cd ../fast_track
BACKEND_COVERAGE_JSON=$PWD/../lightly_studio/coverage.json \
  GUARDRAILS=backend/coverage make run-guardrails

# frontend
cd lightly_studio_view
make test-coverage               # writes coverage/coverage-final.json
cd ../fast_track
FRONTEND_COVERAGE_JSON=$PWD/../lightly_studio_view/coverage/coverage-final.json \
  GUARDRAILS=frontend/coverage make run-guardrails
```

## Toolchain

- **Node** floor enforced by `engine-strict` + `engines` (`>=24`); the exact
  version (`24.13.1`) is pinned in [`.nvmrc`](.nvmrc) for `nvm`/`make` users.
- **TypeScript** in `--noEmit` mode — type-checking only; code runs via `tsx`.
- **ESLint 9** flat config + `typescript-eslint`, with `eslint-config-prettier`
  so formatting is Prettier's job alone.
- **Prettier** for formatting.
- **Vitest** for unit tests (`*.test.ts` next to their source).
