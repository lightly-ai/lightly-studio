---
name: backend-guide
description: Read before adding or changing backend code in lightly_studio - FastAPI routes, services, resolvers, SQLModel tables, or database access. Explains the api/services/resolvers/models layering, the Base/Create/Table/View model split, request flow, error handling, DuckDB and PostgreSQL persistence, Alembic migrations, and how to navigate the package.
---

# Backend Architecture Overview

The backend lives in `lightly_studio/src/lightly_studio`. It is a Python package that can run as a local app, expose a FastAPI server, and serve the built web UI.

## Core technologies

- `FastAPI` provides the HTTP API and application lifecycle.
- `Pydantic` is used for request and response models, validation, and OpenAPI schema generation.
- `SQLModel` is used for database models and typed database access on top of SQLAlchemy sessions.
- The database layer supports `DuckDB` by default and `PostgreSQL` as an alternative backend.
- `uvicorn` runs the backend server.

## Main packages

- `api/`: FastAPI app setup, route registration, exception handling, media endpoints, and webapp serving. `api/app.py` is the composition root. The API routes are in `api/routes/api/`.
- `services/`: Small orchestration layer for workflows that span multiple resolvers or need branching business logic. Not every endpoint needs a service.
- `resolvers/`: Database-facing query and mutation functions. This is where most persistence logic lives.
    - A resolver package has one public function per file, and `<entity>_resolver/__init__.py` exports it. Private helpers of that function stay in the same file.
    - The tests use the same layout: `tests/resolvers/<entity>_resolver/test_<function>.py`.
    - Resolvers and services call `session.commit()`. Routes do not.
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

- Raise a domain error from `errors.py`, for example `NotFoundError`. Add a new error class there
  if none fits.
- `api/routes/api/exceptions.py` has the handlers that convert these errors to HTTP responses. A
  new error class needs a handler there.
- Do not raise `HTTPException`. Existing routes that raise it are legacy; do not copy them, and
  convert a route when you change it.
- Use the `HTTP_STATUS_*` constants from `api/routes/api/status.py`, not numeric literals.
- Do not catch an exception in a resolver or a service to convert it. Let it go to the `api/`
  layer.

```python
# Bad
if tag is None:
    raise HTTPException(status_code=404, detail="Tag not found")

# Good
if tag is None:
    raise NotFoundError(f"Tag {tag_id} does not exist.")
```

## Runtime, persistence and the database

- `database/db_manager.py` centralizes engine and session management.
- FastAPI dependencies provide short-lived sessions for request handling. A route gets its session from the `SessionDep` argument type by default. The media routes (`api/routes/images.py`, `video_media.py`, `video_frames_media.py`) do not use `SessionDep`: they open and close a session before the file I/O, because the dependency holds a thread pool slot for the full request.
- The app lifespan also initializes and shuts down plugins, then closes the database engine cleanly.
- Python API classes in `core/` use a long-lived `db_manager.persistent_session()`. Currently this is a design limitation, causing issues with DuckDB's single-writer model.

### DuckDB

Schema is created with `SQLModel.metadata.create_all()` on startup.

### PostgreSQL and Alembic

A change to a `*Table` model needs an Alembic revision: `make migration-revision-postgresql MSG=<name>`.
See `lightly_studio/MIGRATIONS.md` for full details on Alembic setup, startup behavior, adding schema changes, and validation.

## Build and generated artifacts

- The Python package is built from `lightly_studio/pyproject.toml` with `uv build`.
- The backend package build depends on `make build-lightly_studio_view`, which first exports backend-generated artifacts and then builds the frontend.
- OpenAPI is generated from the FastAPI app with `uv run src/lightly_studio/export_schema.py`, which serializes `app.openapi()` to `openapi.json`.
- The frontend uses that generated schema for API type generation before its own build.
- After `lightly_studio_view` is built, its static output is copied into `lightly_studio/src/lightly_studio/dist_lightly_studio_view_app`.
- `api/routes/webapp.py` serves that bundled frontend from inside the Python package, so the shipped backend can serve the UI directly.

## How to navigate the codebase

- Start in `api/routes/` if the change is triggered by an HTTP endpoint. Most routes are in `api/routes/api/`; the media, MCAP sequence, and recording routes are next to it.
- Check `services/` when the endpoint coordinates multiple entities or sample types.
- Go to `resolvers/` for query logic, filtering, and persistence details.
- Look in `models/` for request bodies, response models, and database tables.
- Tests mirror this split under `lightly_studio/tests/`.
