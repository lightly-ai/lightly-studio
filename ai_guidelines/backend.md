# Backend Architecture Overview

The backend lives in `lightly_studio/src/lightly_studio`. It is a Python package that can run as a local app, expose a FastAPI server, and serve the built web UI.

## Core technologies

- `FastAPI` provides the HTTP API and application lifecycle.
- `Pydantic` is used for request and response models, validation, and OpenAPI schema generation.
- `SQLModel` is used for database models and typed database access on top of SQLAlchemy sessions.
- The database layer supports `DuckDB` by default and `PostgreSQL` as an alternative backend.
- `uvicorn` runs the backend server.

## Main packages

- `api/`: FastAPI app setup, route registration, exception handling, media endpoints, and webapp serving. `api/app.py` is the composition root.
- `services/`: Small orchestration layer for workflows that span multiple resolvers or need branching business logic. Not every endpoint needs a service.
- `resolvers/`: Database-facing query and mutation functions. This is where most persistence logic lives.
- `models/`: SQLModel tables plus Pydantic/SQLModel request and view models shared across layers.
- `core/`, `dataset/`, `export/`, `metadata/`, `plugins/`, `few_shot_classifier/`: Product-specific modules used by routes, services, or resolvers when the logic is not just CRUD.

## Model organization

Backend models are usually split by role within the same module:

- `*Base`: shared fields
- `*Create`: input model for inserts
- `*Table`: SQLModel table mapped to the database
- `*View`: API-facing response model
- `*WithCount` or similar wrappers: list responses with pagination or metadata

Keep database tables and API views separate even when they look similar. This keeps persistence concerns, validation, and response shaping explicit.

## Request flow

Most request paths follow this shape:

```text
FastAPI route -> optional service -> resolver(s) -> SQLModel / database
```

Use the layers with the following intent:

- Routes translate HTTP input into typed models, wire dependencies, and map failures to HTTP responses.
- Services coordinate multiple resolvers or enforce workflow-specific rules.
- Resolvers own database access and reusable queries.

Thin endpoints may call resolvers directly. Services are mainly for cross-entity operations, not as a mandatory wrapper around every route.

## Error handling

- Raise specific exceptions in the `api/` layer. FastAPI will handle converting them to HTTP responses. Do not raise `HTTPException` directly.
- We let exceptions raised from the rest of Python code propagate cleanly to the api layer, and be ultimately handled by FastAPI.

## Runtime, persistence and the database

- `db_manager.py` centralizes engine and session management.
- FastAPI dependencies provide short-lived sessions for request handling.
- The app lifespan also initializes and shuts down plugins, then closes the database engine cleanly.
- Python API classes in `core/` use a long-lived `db_manager.persistent_session()`. Currently this is a design limitation, causing issues with DuckDB's single-writer model.

### DuckDB

Schema is created with `SQLModel.metadata.create_all()` on startup.

### PostgreSQL and Alembic

Schema changes for PostgreSQL use [Alembic](https://alembic.sqlalchemy.org/). Migration scripts live in `src/lightly_studio/migrations/versions/`; configuration in `alembic.ini` and `migrations/env.py`. Runtime logic is in `db_migrations.run_migrations()`.

**Startup** (Postgres only):

| Database state | On connect | What runs |
|----------------|------------|-----------|
| Empty (no `alembic_version`, no app tables) | `upgrade head` | All revision scripts from the start (e.g. baseline → `head`) |
| `alembic_version` present | `upgrade head` | Pending revisions from current version → `head` |

Empty and tracked databases both build schema via Alembic `upgrade head`, not `SQLModel.metadata.create_all()`. The difference is scope: a fresh database replays the full chain; a tracked database applies only migrations not yet in `alembic_version`.

The `alembic_version` table stores the current revision id, not the product version string. Map product releases (e.g. v5 → v10) to revision ids in release notes.

`cleanup_existing=True` on Postgres drops all tables (including `alembic_version`), then runs `upgrade head` on the empty database.

**Local Postgres** (required for autogenerate and migration checks):

```bash
cd lightly_studio
make start-postgres
```

Set `LIGHTLY_STUDIO_DATABASE_URL` to the dev URL (the Makefile uses `postgresql://lightly:lightly@localhost:5433/lightly_studio` via `POSTGRES_URL`).

Makefile targets: `migration-upgrade-postgresql`, `migration-revision-postgresql` (requires `MSG=...`), `migration-stamp-postgresql`, `migration-downgrade-postgresql` (dev only), `migration-check-postgresql` (empty DB: `upgrade head` + `alembic check`).

**Adding a schema change** (append a new revision; do not edit the baseline):

1. Change SQLModel tables in code (on a branch where migration files already define the **previous** head).
2. Run `make migration-revision-postgresql MSG=short_description` (runs `migration-upgrade-postgresql` first so the dev database matches the current head, then autogenerates the delta).
3. Review the generated file under `src/lightly_studio/migrations/versions/`, commit the model change and the new revision together.

Use a quoted `MSG` when it contains spaces, e.g. `make migration-revision-postgresql MSG="updated db"`.

**Validation:**

```bash
cd lightly_studio
make static-checks
make test
make migration-check-postgresql
make test-postgres
```

## Build and generated artifacts

- The Python package is built from `lightly_studio/pyproject.toml` with `uv build`.
- The backend package build depends on `make build-lightly_studio_view`, which first exports backend-generated artifacts and then builds the frontend.
- OpenAPI is generated from the FastAPI app with `uv run src/lightly_studio/export_schema.py`, which serializes `app.openapi()` to `openapi.json`.
- The frontend uses that generated schema for API type generation before its own build.
- After `lightly_studio_view` is built, its static output is copied into `lightly_studio/src/lightly_studio/dist_lightly_studio_view_app`.
- `api/routes/webapp.py` serves that bundled frontend from inside the Python package, so the shipped backend can serve the UI directly.

## How to navigate the codebase

- Start in `api/routes/` if the change is triggered by an HTTP endpoint.
- Check `services/` when the endpoint coordinates multiple entities or sample types.
- Go to `resolvers/` for query logic, filtering, and persistence details.
- Look in `models/` for request bodies, response models, and database tables.
- Tests mirror this split under `lightly_studio/tests/`.
