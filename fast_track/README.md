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
is set up with CODEOWNERS so that for certain paths a Lightly team member approval
is required. In particular, if the code touches guardrails or CI.

The bot is benevolent in dismissing its past approvals. It does so only when a new bot run
(after a new push) observes failed guardrails. Therefore there is a window when the PR
might be approved but the newest potentially failing commit would fail the guardrails.
This is intentional; it alignes with the current philosophy of not dismissing stale approvals
to allow a faster development cycle.

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

## `backend/coverage`

**What it does.** For every backend source file the PR touches, it asks: are the
lines this PR _added_ covered by tests? Each file is judged on its own at
**90%**. Coverage is not pooled, so one well-covered file cannot carry an
uncovered one. The guardrail never runs tests itself; it only reads a report.

**Inputs.** Two, combined per file:

| input      | source                                                            |
| ---------- | ----------------------------------------------------------------- |
| the diff   | `BASE_REF...HEAD`, giving the added line numbers per changed file |
| the report | a full-suite `coverage.py` JSON report, produced by the workflow  |

The report arrives through two env vars:

| var                     | meaning                               |
| ----------------------- | ------------------------------------- |
| `BACKEND_COVERAGE_JSON` | path to the `coverage.py` JSON report |
| `BACKEND_TESTS_PASSED`  | `false` when that test run failed     |

**When to expect a verdict.** Only when the PR changes backend source, i.e.
`lightly_studio/src/lightly_studio/**/*.py`. Tests, `conftest.py`, `__init__.py`
and the `migrations/`, `examples/` and `vendor/` trees are out of scope; a PR
touching nothing else passes as `0 file(s) checked`. The workflow runs the full
suite on the same path filter, so the expensive step is skipped for PRs this
guardrail would not judge anyway.

Verdicts:

- no changed file in scope → pass, `0 file(s) checked`
- report present → each file judged at 90%; a file the report omits fails
- env var set but the file is missing → fail, `coverage report missing`
- `BACKEND_TESTS_PASSED=false` → fail, coverage is not judged on partial data
- **env var unset** → pass, with a loud `coverage skipped` summary. Only the
  local `make run-guardrails` path reaches this; CI always sets the var.

To exercise it locally, produce a report and point the guardrail at it:

```bash
cd lightly_studio
make build-lightly_studio_view   # conftest imports the app, so the dist must exist
make install-optional-deps       # some test modules need extras (e.g. s3fs)
make test-coverage               # writes lightly_studio/coverage.json

cd ../fast_track
BACKEND_COVERAGE_JSON=$PWD/../lightly_studio/coverage.json \
  GUARDRAILS=backend/coverage make run-guardrails
```

## Toolchain

- **Node** floor enforced by `engine-strict` + `engines` (`>=24`); the exact
  version (`24.13.1`) is pinned in [`.nvmrc`](.nvmrc) for `nvm`/`make` users.
- **TypeScript** in `--noEmit` mode — type-checking only; code runs via `tsx`.
- **ESLint 9** flat config + `typescript-eslint`, with `eslint-config-prettier`
  so formatting is Prettier's job alone.
- **Prettier** for formatting.
- **Vitest** for unit tests (`*.test.ts` next to their source).
