# Postgres E2E test configuration
POSTGRES_CONTAINER_NAME := lightly-studio-postgres
POSTGRES_PORT := 5433
POSTGRES_USER := lightly
POSTGRES_PASSWORD := lightly
POSTGRES_DB := lightly_studio
POSTGRES_IMAGE := pgvector/pgvector:0.8.1-pg18-bookworm
POSTGRES_SHM_SIZE ?= 2g
POSTGRES_URL ?= postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost:$(POSTGRES_PORT)/$(POSTGRES_DB)
POSTGRES_STARTUP_TIMEOUT_SECONDS ?= 60

.PHONY: install-uv
install-uv:
ifeq ($(OS),Windows_NT)
	powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
else
	@if ! command -v uv &> /dev/null; then \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
endif

# Note: Install target with default dependencies is not necessary as uv will
# install the default dependencies automatically on e.g. `uv run` etc.
.PHONY: install-optional-deps
install-optional-deps:
	@echo "Installing with optional dependencies..."
	uv sync --all-groups --all-extras

.PHONY: build
build: clean build-lightly_studio_view
	@echo "Building a distribution package..."
	uv build

.PHONY: build-lightly_studio_view
build-lightly_studio_view: export-schema export-version
ifeq ($(OS),Windows_NT)
	@powershell -Command "$$env:PUBLIC_POSTHOG_KEY='$(PUBLIC_POSTHOG_KEY)'; $(MAKE) -C ../lightly_studio_view build"
	@powershell -Command "New-Item -ItemType Directory -Path src\\lightly_studio\\dist_lightly_studio_view_app -Force -ErrorAction SilentlyContinue | Out-Null"
	@powershell -Command "Copy-Item -Path ..\lightly_studio_view\build\* -Destination src\lightly_studio\dist_lightly_studio_view_app\ -Recurse -Force"
	@powershell -Command "Copy-Item -Path ..\lightly_studio_view\src\lib\version.json -Destination src\lightly_studio\dist_lightly_studio_view_app\version-info.json -Force"
else
	PUBLIC_POSTHOG_KEY=$(PUBLIC_POSTHOG_KEY) $(MAKE) -C ../lightly_studio_view build
	cp -r ../lightly_studio_view/build/ src/lightly_studio/dist_lightly_studio_view_app
	cp ../lightly_studio_view/src/lib/version.json src/lightly_studio/dist_lightly_studio_view_app/version-info.json
endif

# Fast build: skips npm ci, nvm install, and langium generate in the frontend.
.PHONY: build-dirty
build-dirty: build-dirty-lightly_studio_view
	@echo "Building a distribution package..."
	uv build

.PHONY: build-dirty-lightly_studio_view
build-dirty-lightly_studio_view: export-schema export-version
ifeq ($(OS),Windows_NT)
	@powershell -Command "$$env:PUBLIC_POSTHOG_KEY='$(PUBLIC_POSTHOG_KEY)'; $(MAKE) -C ../lightly_studio_view build-dirty"
	@powershell -Command "New-Item -ItemType Directory -Path src\\lightly_studio\\dist_lightly_studio_view_app -Force -ErrorAction SilentlyContinue | Out-Null"
	@powershell -Command "Copy-Item -Path ..\lightly_studio_view\build\* -Destination src\lightly_studio\dist_lightly_studio_view_app\ -Recurse -Force"
	@powershell -Command "Copy-Item -Path ..\lightly_studio_view\src\lib\version.json -Destination src\lightly_studio\dist_lightly_studio_view_app\version-info.json -Force"
else
	PUBLIC_POSTHOG_KEY=$(PUBLIC_POSTHOG_KEY) $(MAKE) -C ../lightly_studio_view build-dirty
	cp -r ../lightly_studio_view/build/ src/lightly_studio/dist_lightly_studio_view_app
	cp ../lightly_studio_view/src/lib/version.json src/lightly_studio/dist_lightly_studio_view_app/version-info.json
endif

.PHONY: start
start: build
	$(MAKE) start-example

.PHONY: start-e2e
start-e2e: build
	@echo "Starting server for e2e tests..."
	uv run e2e-tests/index_general.py

.PHONY: start-e2e-with-videos
start-e2e-with-videos: build
	@echo "Starting server for e2e tests with videos..."
	uv run e2e-tests/index_video.py

.PHONY: start-e2e-groups
start-e2e-groups: build
	uv run e2e-tests/index_groups.py

.PHONY: start-e2e-with-predictions
start-e2e-with-predictions: build
	@echo "Starting server for e2e tests with predictions..."
	uv run e2e-tests/index_predictions.py

.PHONY: start-e2e-evaluations
start-e2e-evaluations: build
	@echo "Starting server for e2e tests with evaluations..."
	uv run e2e-tests/index_evaluations.py

# Content is controlled via env vars (all default to true), e.g.:
#   ADD_METADATA=false make start-e2e-distribution
#   ADD_CLASSIFICATIONS=false ADD_OBJECT_DETECTIONS=false ADD_SEGMENTATIONS=false make start-e2e-distribution
.PHONY: start-e2e-distribution
start-e2e-distribution: build
	@echo "Starting server for e2e distribution tests (toggles: ADD_CLASSIFICATIONS, ADD_OBJECT_DETECTIONS, ADD_SEGMENTATIONS, ADD_METADATA)..."
	uv run e2e-tests/index_distribution.py

.PHONY: start-e2e-video-groups
start-e2e-video-groups: build
	uv run e2e-tests/index_videos_groups.py

# See e2e-tests/README.md for S3 setup and credential instructions
.PHONY: start-e2e-s3
start-e2e-s3: build
	@echo "Starting server for e2e tests with remote S3 dataset..."
	uv run e2e-tests/index_s3.py

# Uses gcsfs default authentication; see e2e-tests/README.md for alternatives
.PHONY: start-e2e-gcs
start-e2e-gcs: build
	@echo "Starting server for e2e tests with remote GCS dataset..."
	uv run e2e-tests/index_gcs.py

# See e2e-tests/README.md for Azure setup and credential instructions
.PHONY: start-e2e-azure
start-e2e-azure: build
	@echo "Starting server for e2e tests with remote Azure dataset..."
	uv run e2e-tests/index_azure.py

.PHONY: start-postgres
start-postgres: stop-postgres
	@echo "Starting PostgreSQL container ($(POSTGRES_IMAGE))..."
	docker run -d \
		--name $(POSTGRES_CONTAINER_NAME) \
		--shm-size=$(POSTGRES_SHM_SIZE) \
		-e POSTGRES_USER=$(POSTGRES_USER) \
		-e POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
		-e POSTGRES_DB=$(POSTGRES_DB) \
		-p $(POSTGRES_PORT):5432 \
		$(POSTGRES_IMAGE)
	@echo "Waiting for PostgreSQL to be ready..."
# Probe over TCP (-h 127.0.0.1) with a real query against $(POSTGRES_DB). Both details matter:
# pg_isready only pings the postmaster and reports success even when the database is missing, and
# the entrypoint's temporary bootstrap server -- which creates $(POSTGRES_DB), then runs the init
# scripts and shuts down again -- listens on the Unix socket only. A socket probe therefore
# answers from that short-lived server, so callers reach $(POSTGRES_URL) before the real server
# accepts TCP connections.
ifeq ($(OS),Windows_NT)
	@powershell -Command "$$deadline = (Get-Date).AddSeconds($(POSTGRES_STARTUP_TIMEOUT_SECONDS)); while ($$true) { docker exec -e PGPASSWORD=$(POSTGRES_PASSWORD) $(POSTGRES_CONTAINER_NAME) psql -h 127.0.0.1 -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c 'SELECT 1' *> $$null; if ($$LASTEXITCODE -eq 0) { break }; if ((Get-Date) -ge $$deadline) { Write-Host 'PostgreSQL did not become ready within $(POSTGRES_STARTUP_TIMEOUT_SECONDS) seconds'; docker logs $(POSTGRES_CONTAINER_NAME); exit 1 }; Start-Sleep -Seconds 1 }"
else
	@deadline=$$(($$(date +%s) + $(POSTGRES_STARTUP_TIMEOUT_SECONDS))); \
	until docker exec -e PGPASSWORD=$(POSTGRES_PASSWORD) $(POSTGRES_CONTAINER_NAME) psql -h 127.0.0.1 -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c 'SELECT 1' > /dev/null 2>&1; do \
		if [ $$(date +%s) -ge $$deadline ]; then \
			echo "PostgreSQL did not become ready within $(POSTGRES_STARTUP_TIMEOUT_SECONDS) seconds"; \
			docker logs $(POSTGRES_CONTAINER_NAME); \
			exit 1; \
		fi; \
		sleep 1; \
	done
endif
	@echo "PostgreSQL is ready on port $(POSTGRES_PORT)"

.PHONY: stop-postgres
stop-postgres:
	@echo "Stopping and removing PostgreSQL container..."
	-docker stop $(POSTGRES_CONTAINER_NAME)
	-docker rm $(POSTGRES_CONTAINER_NAME)
	@echo "PostgreSQL container removed"

.PHONY: start-e2e-postgres
start-e2e-postgres: build
	@echo "Starting server for e2e tests with PostgreSQL..."
	LIGHTLY_STUDIO_DATABASE_URL=$(POSTGRES_URL) uv run e2e-tests/index_general.py

.PHONY: start-e2e-postgres-with-videos
start-e2e-postgres-with-videos: build
	@echo "Starting server for e2e tests with videos on PostgreSQL..."
	LIGHTLY_STUDIO_DATABASE_URL=$(POSTGRES_URL) uv run e2e-tests/index_video.py

.PHONY: start-e2e-postgres-groups
start-e2e-postgres-groups: build
	LIGHTLY_STUDIO_DATABASE_URL=$(POSTGRES_URL) uv run e2e-tests/index_groups.py

.PHONY: start-e2e-postgres-video-groups
start-e2e-postgres-video-groups: build
	LIGHTLY_STUDIO_DATABASE_URL=$(POSTGRES_URL) uv run e2e-tests/index_videos_groups.py

# Note: we just mock dist_lightly_studio_view_app folder to avoid failing exporting the schema
# because we need to have schema before building the frontend app
.PHONY: export-schema
export-schema:
ifeq ($(OS),Windows_NT)
	@powershell -Command "if (-not (Test-Path src\lightly_studio\dist_lightly_studio_view_app)) { New-Item -ItemType Directory -Path src\lightly_studio\dist_lightly_studio_view_app | Out-Null }"
	@powershell -Command "New-Item -ItemType File -Path src\lightly_studio\dist_lightly_studio_view_app\index.html -Force | Out-Null"
	@echo "Exporting schema for API..."
	uv run src/lightly_studio/export_schema.py
	@powershell -Command "Remove-Item -Path src\lightly_studio\dist_lightly_studio_view_app -Recurse -Force -ErrorAction SilentlyContinue"
else
	mkdir -p src/lightly_studio/dist_lightly_studio_view_app
	touch src/lightly_studio/dist_lightly_studio_view_app/index.html
	@echo "Exporting schema for API..."
	uv run src/lightly_studio/export_schema.py
	rm -rf src/lightly_studio/dist_lightly_studio_view_app
endif

.PHONY: export-version
export-version:
	@echo "Exporting version information for lightly_studio_view..."
	uv run src/lightly_studio/export_version.py --output ../lightly_studio_view/src/lib/version.json

.PHONY: start-example
start-example:
	@echo "Starting server..."
	uv run src/lightly_studio/examples/example.py

.PHONY: test
test: build
	@echo "Running tests..."
	PYTHONPATH=$(PWD) uv run pytest -n auto

.PHONY: test-ci
test-ci:
	@echo "Running tests..."
	uv run pytest

# Full-suite line coverage for the Fast Track coverage guardrail, which reads
# coverage.json rather than running tests itself. Deliberately has no `build`
# prerequisite: its `clean` step would delete a webapp build the caller made.
.PHONY: test-coverage
test-coverage:
	@echo "Running tests with coverage..."
	uv run pytest -n auto --cov=src/lightly_studio \
	  --cov-report=json:coverage.json \
	  --cov-report=term-missing:skip-covered

.PHONY: test-postgres
test-postgres: build
	@echo "Running tests against Postgres..."
	uv run pytest --postgres -n 3

# Alembic loads lightly_studio package code that expects dist_lightly_studio_view_app.
.PHONY: mock-webapp-dist
mock-webapp-dist:
ifeq ($(OS),Windows_NT)
	@powershell -Command "if (-not (Test-Path src\lightly_studio\dist_lightly_studio_view_app)) { New-Item -ItemType Directory -Path src\lightly_studio\dist_lightly_studio_view_app | Out-Null }; New-Item -ItemType File -Path src\lightly_studio\dist_lightly_studio_view_app\index.html -Force | Out-Null"
else
	@mkdir -p src/lightly_studio/dist_lightly_studio_view_app
	@touch src/lightly_studio/dist_lightly_studio_view_app/index.html
endif

.PHONY: migration-upgrade-postgresql
migration-upgrade-postgresql: start-postgres mock-webapp-dist
	@echo "Applying Alembic migrations (upgrade head)..."
ifeq ($(OS),Windows_NT)
	@powershell -Command "$$env:LIGHTLY_STUDIO_DATABASE_URL='$(POSTGRES_URL)'; uv run alembic -c alembic.ini upgrade head"
else
	LIGHTLY_STUDIO_DATABASE_URL=$(POSTGRES_URL) uv run alembic -c alembic.ini upgrade head
endif


.PHONY: migration-downgrade-postgresql
migration-downgrade-postgresql: start-postgres mock-webapp-dist
	@echo "Downgrading Alembic by one revision (dev only)..."
ifeq ($(OS),Windows_NT)
	@powershell -Command "$$env:LIGHTLY_STUDIO_DATABASE_URL='$(POSTGRES_URL)'; uv run alembic -c alembic.ini downgrade -1"
else
	LIGHTLY_STUDIO_DATABASE_URL=$(POSTGRES_URL) uv run alembic -c alembic.ini downgrade -1
endif

# Autogenerate requires the database schema to match the current Alembic head.
.PHONY: migration-revision-postgresql
migration-revision-postgresql: migration-upgrade-postgresql
ifndef MSG
	$(error MSG is required. Example: make migration-revision-postgresql MSG=add_column)
endif
	@echo "Autogenerating Alembic revision..."
ifeq ($(OS),Windows_NT)
	@powershell -Command "$$env:LIGHTLY_STUDIO_DATABASE_URL='$(POSTGRES_URL)'; uv run alembic -c alembic.ini revision --autogenerate -m '$(MSG)'"
else
	LIGHTLY_STUDIO_DATABASE_URL=$(POSTGRES_URL) uv run alembic -c alembic.ini revision --autogenerate -m "$(MSG)"
endif

.PHONY: migration-check-postgresql
migration-check-postgresql: start-postgres mock-webapp-dist
	@echo "Checking Alembic migration chain on empty Postgres..."
ifeq ($(OS),Windows_NT)
	@powershell -Command "docker exec $(POSTGRES_CONTAINER_NAME) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c \"DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO $(POSTGRES_USER); GRANT ALL ON SCHEMA public TO public;\""
	@powershell -Command "$$env:LIGHTLY_STUDIO_DATABASE_URL='$(POSTGRES_URL)'; uv run alembic -c alembic.ini upgrade head"
	@powershell -Command "$$env:LIGHTLY_STUDIO_DATABASE_URL='$(POSTGRES_URL)'; uv run alembic -c alembic.ini check"
else
	docker exec $(POSTGRES_CONTAINER_NAME) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO $(POSTGRES_USER); GRANT ALL ON SCHEMA public TO public;"
	LIGHTLY_STUDIO_DATABASE_URL=$(POSTGRES_URL) uv run alembic -c alembic.ini upgrade head
	LIGHTLY_STUDIO_DATABASE_URL=$(POSTGRES_URL) uv run alembic -c alembic.ini check
endif

.PHONY: check-uv-lock
check-uv-lock:
	@echo "Ensuring uv.lock is up to date..."
	uv lock --check

.PHONY: lint
lint:
	@echo "Linting project with ruff..."
	uv run ruff check

.PHONY: type-check
type-check:
	@echo "Checking types with mypy..."
	uv run mypy .

.PHONY: format-check
format-check:
	@echo "Checking format with ruff..."
	uv run ruff format --check

.PHONY: static-checks
static-checks: check-uv-lock lint type-check format-check

.PHONY: format
format:
	@echo "Formatting project with ruff..."
	uv run ruff format
	uv run ruff check --fix

.PHONY: lint-fix
lint-fix:
	uv run ruff check --fix

.PHONY: clean
clean:
ifeq ($(OS),Windows_NT)
	@powershell -Command "Get-ChildItem -Path . -Filter *.db -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Get-ChildItem -Path . -Filter *.db.wal -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue"
	@powershell -Command "if (Test-Path dist) { Get-ChildItem -Path dist -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue }"
	@powershell -Command "if (Test-Path src\lightly_studio\dist_lightly_studio_view_app) { Remove-Item -Path src\lightly_studio\dist_lightly_studio_view_app -Recurse -Force -ErrorAction SilentlyContinue }"
	@powershell -Command "Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Get-ChildItem -Path . -Recurse -Directory -Filter *.egg-info -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
else
	rm -rf *.db
	rm -rf *.db.wal
	rm -rf dist/*
	rm -rf src/lightly_studio/dist_lightly_studio_view_app
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.egg-info" -type d -exec rm -rf {} +
endif
