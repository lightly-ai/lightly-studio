# Postgres E2E test configuration (for local development only, not used in CI)
POSTGRES_CONTAINER_NAME := lightly-studio-postgres
POSTGRES_PORT := 5434
POSTGRES_USER := lightly
POSTGRES_PASSWORD := lightly
POSTGRES_DB := lightly_studio
POSTGRES_IMAGE := pgvector/pgvector:0.8.1-pg18-bookworm
POSTGRES_URL ?= postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost:$(POSTGRES_PORT)/$(POSTGRES_DB)

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
	@echo "Installing keyring provider for Google Artifact Registry..."
# Install keyring in the global python environment. It is not possible to install it
# in the uv environment because uv needs it already during `uv sync`. Note that
# we cannot use `uv tool` because it does not support tool installations for more
# than one python version at the same time.
	pip install keyrings.google-artifactregistry-auth
	@echo "Installing with optional dependencies..."
	uv sync --all-groups --all-extras

.PHONY: build
build: clean build-lightly_studio_view
	@echo "Building a distribution package..."
	uv build

.PHONY: build-lightly_studio_view
build-lightly_studio_view: export-schema export-version
ifeq ($(OS),Windows_NT)
	@powershell -Command "$$env:PUBLIC_POSTHOG_KEY='$(PUBLIC_POSTHOG_KEY)'; make -C ../lightly_studio_view build"
	@powershell -Command "New-Item -ItemType Directory -Path src\\lightly_studio\\dist_lightly_studio_view_app -Force -ErrorAction SilentlyContinue | Out-Null"
	@powershell -Command "Copy-Item -Path ..\lightly_studio_view\build\* -Destination src\lightly_studio\dist_lightly_studio_view_app\ -Recurse -Force"
else
	PUBLIC_POSTHOG_KEY=$(PUBLIC_POSTHOG_KEY) make -C ../lightly_studio_view build
	cp -r ../lightly_studio_view/build/ src/lightly_studio/dist_lightly_studio_view_app
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

.PHONY: start-e2e-video-groups
start-e2e-video-groups: build
	uv run e2e-tests/index_videos_groups.py

.PHONY: start-postgres
start-postgres: stop-postgres
	@echo "Starting PostgreSQL container ($(POSTGRES_IMAGE))..."
	docker run -d \
		--name $(POSTGRES_CONTAINER_NAME) \
		-e POSTGRES_USER=$(POSTGRES_USER) \
		-e POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
		-e POSTGRES_DB=$(POSTGRES_DB) \
		-p $(POSTGRES_PORT):5432 \
		$(POSTGRES_IMAGE)
ifeq ($(OS),Windows_NT)
	@powershell -Command "Start-Sleep -Seconds 3"
else
	@echo "Waiting for PostgreSQL to be ready..."
	@until docker exec $(POSTGRES_CONTAINER_NAME) pg_isready -U $(POSTGRES_USER) -d $(POSTGRES_DB) > /dev/null 2>&1; do \
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
	PYTHONPATH=$(PWD) uv run pytest

.PHONY: test-ci
test-ci:
	@echo "Running tests..."
	uv run pytest

.PHONY: test-postgres
test-postgres: build
	@echo "Running tests against Postgres..."
	uv run pytest --postgres

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
