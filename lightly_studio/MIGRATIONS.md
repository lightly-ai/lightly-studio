# Database Migrations

Schema changes for PostgreSQL use [Alembic](https://alembic.sqlalchemy.org/). Migration scripts live in `src/lightly_studio/migrations/versions/`; configuration in `alembic.ini` and `migrations/env.py`. Runtime logic is in `db_migrations.run_migrations()`.

## Startup behavior (Postgres only)

| Database state | On connect | What runs |
|----------------|------------|-----------|
| Empty (no `alembic_version`, no app tables) | `upgrade head` | All revision scripts from the start (e.g. baseline → `head`) |
| `alembic_version` present | `upgrade head` | Pending revisions from current version → `head` |

Empty and tracked databases both build schema via Alembic `upgrade head`, not `SQLModel.metadata.create_all()`. The difference is scope: a fresh database replays the full chain; a tracked database applies only migrations not yet in `alembic_version`.

The `alembic_version` table stores the current revision id, not the product version string. Map product releases (e.g. v5 → v10) to revision ids in release notes.

`cleanup_existing=True` on Postgres drops all tables (including `alembic_version`), then runs `upgrade head` on the empty database.

## Local Postgres setup

Required for autogenerate and migration checks:

```bash
cd lightly_studio
make start-postgres
```

Set `LIGHTLY_STUDIO_DATABASE_URL` to the dev URL (the Makefile uses `postgresql://lightly:lightly@localhost:5433/lightly_studio` via `POSTGRES_URL`).

Makefile targets: `migration-upgrade-postgresql`, `migration-revision-postgresql` (requires `MSG=...`), `migration-downgrade-postgresql` (dev only), `migration-check-postgresql` (empty DB: `upgrade head` + `alembic check`).

## Adding a schema change

Append a new revision; do not edit the baseline:

1. Change SQLModel tables in code (on a branch where migration files already define the **previous** head).
2. Run `make migration-revision-postgresql MSG=short_description` (runs `migration-upgrade-postgresql` first so the dev database matches the current head, then autogenerates the delta).
3. Review the generated file under `src/lightly_studio/migrations/versions/`, commit the model change and the new revision together.

Use a quoted `MSG` when it contains spaces, e.g. `make migration-revision-postgresql MSG="updated db"`.

## Validation

```bash
cd lightly_studio
make static-checks
make test
make migration-check-postgresql
make test-postgres
```
