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

# Floci (AWS S3 emulator) development storage for MCAP recordings.
FLOCI_CONTAINER_NAME := lightly-studio-floci
FLOCI_PORT ?= 4566
FLOCI_STARTUP_TIMEOUT_SECONDS ?= 60
FLOCI_S3_BUCKET ?= lightly-studio
FLOCI_S3_PREFIX ?= recordings
# Space-separated local files, e.g.:
#   make setup-floci FLOCI_MCAP_FILES="~/data/front.mcap ~/data/rear.mcap"
FLOCI_MCAP_FILES ?= datasets/mcap/perception.mcap
FLOCI_ENV := AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1 \
	AWS_ENDPOINT_URL=http://localhost:$(FLOCI_PORT)

# Floci GCP (GCS emulator) development storage for MCAP recordings.
FLOCI_GCP_CONTAINER_NAME := lightly-studio-floci-gcp
FLOCI_GCP_PORT ?= 4588
FLOCI_GCP_STARTUP_TIMEOUT_SECONDS ?= 60
FLOCI_GCP_BUCKET ?= lightly-studio
FLOCI_GCP_PREFIX ?= recordings
# Space-separated local files, e.g.:
#   make setup-floci-gcp FLOCI_GCP_MCAP_FILES="~/data/front.mcap ~/data/rear.mcap"
FLOCI_GCP_MCAP_FILES ?= datasets/mcap/perception.mcap
FLOCI_GCP_ENV := STORAGE_EMULATOR_HOST=http://localhost:$(FLOCI_GCP_PORT)

# Installs the uv version that `required-version` in pyproject.toml pins, so a local
# `uv lock` writes the same file the workflows do. Keep the version in sync with that pin.
UV_VERSION := 0.12.6

.PHONY: install-uv
install-uv:
ifeq ($(OS),Windows_NT)
	powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/$(UV_VERSION)/install.ps1 | iex"
else
	@if [ "$$(uv --version 2>/dev/null | awk '{print $$2}')" != "$(UV_VERSION)" ]; then \
		set -e; \
		installer=$$(mktemp); \
		trap 'rm -f "$$installer"' EXIT; \
		curl -LsSf https://astral.sh/uv/$(UV_VERSION)/install.sh -o "$$installer"; \
		sh "$$installer"; \
		[ "$$(uv --version 2>/dev/null | awk '{print $$2}')" = "$(UV_VERSION)" ] || \
			echo "Installed uv $(UV_VERSION). Restart your shell, or fix your PATH if another uv shadows it."; \
	fi
endif

# Note: Install target with default dependencies is not necessary as uv will
# install the default dependencies automatically on e.g. `uv run` etc.
.PHONY: install-optional-deps
install-optional-deps:
	@echo "Installing with optional dependencies..."
	uv sync --all-groups --all-extras

# `--out-dir dist` on every `uv build` below: in a uv workspace `uv build` defaults to the
# workspace root, so without it the wheel would land in ../dist instead of lightly_studio/dist.
.PHONY: build
build: clean build-lightly_studio_view
	@echo "Building a distribution package..."
	uv build --out-dir dist

.PHONY: build-lightly_studio_view
build-lightly_studio_view: export-schema export-version
ifeq ($(OS),Windows_NT)
	@powershell -Command "$(MAKE) -C ../lightly_studio_view build"
	@powershell -Command "New-Item -ItemType Directory -Path src\\lightly_studio\\dist_lightly_studio_view_app -Force -ErrorAction SilentlyContinue | Out-Null"
	@powershell -Command "Copy-Item -Path ..\lightly_studio_view\build\* -Destination src\lightly_studio\dist_lightly_studio_view_app\ -Recurse -Force"
	@powershell -Command "Copy-Item -Path ..\lightly_studio_view\src\lib\version.json -Destination src\lightly_studio\dist_lightly_studio_view_app\version-info.json -Force"
else
	$(MAKE) -C ../lightly_studio_view build
	cp -r ../lightly_studio_view/build/ src/lightly_studio/dist_lightly_studio_view_app
	cp ../lightly_studio_view/src/lib/version.json src/lightly_studio/dist_lightly_studio_view_app/version-info.json
endif

# Fast build: skips npm ci, nvm install, and langium generate in the frontend.
.PHONY: build-dirty
build-dirty: build-dirty-lightly_studio_view
	@echo "Building a distribution package..."
	uv build --out-dir dist

.PHONY: build-dirty-lightly_studio_view
build-dirty-lightly_studio_view: export-schema export-version
ifeq ($(OS),Windows_NT)
	@powershell -Command "$(MAKE) -C ../lightly_studio_view build-dirty"
	@powershell -Command "New-Item -ItemType Directory -Path src\\lightly_studio\\dist_lightly_studio_view_app -Force -ErrorAction SilentlyContinue | Out-Null"
	@powershell -Command "Copy-Item -Path ..\lightly_studio_view\build\* -Destination src\lightly_studio\dist_lightly_studio_view_app\ -Recurse -Force"
	@powershell -Command "Copy-Item -Path ..\lightly_studio_view\src\lib\version.json -Destination src\lightly_studio\dist_lightly_studio_view_app\version-info.json -Force"
else
	$(MAKE) -C ../lightly_studio_view build-dirty
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

.PHONY: start-floci
start-floci:
	@docker rm -f $(FLOCI_CONTAINER_NAME) >/dev/null 2>&1 || true
	@docker run -d --name $(FLOCI_CONTAINER_NAME) -p $(FLOCI_PORT):4566 \
		-v /var/run/docker.sock:/var/run/docker.sock -u root floci/floci:latest
	@echo "Waiting for Floci..."
	@deadline=$$(($$(date +%s) + $(FLOCI_STARTUP_TIMEOUT_SECONDS))); \
	until curl -sf http://localhost:$(FLOCI_PORT)/_floci/health >/dev/null; do \
		if [ $$(date +%s) -ge $$deadline ]; then \
			echo "Floci did not become ready within $(FLOCI_STARTUP_TIMEOUT_SECONDS) seconds"; \
			docker logs $(FLOCI_CONTAINER_NAME); \
			exit 1; \
		fi; \
		sleep 1; \
	done
	@$(FLOCI_ENV) aws s3 mb s3://$(FLOCI_S3_BUCKET) 2>/dev/null || true
	@echo "Floci is ready at http://localhost:$(FLOCI_PORT)"

.PHONY: setup-floci
setup-floci: start-floci
	@for file in $(FLOCI_MCAP_FILES); do \
		key="$(FLOCI_S3_PREFIX)/$$(basename "$$file")"; \
		echo "Uploading $$file to s3://$(FLOCI_S3_BUCKET)/$$key..."; \
		$(FLOCI_ENV) aws s3 cp "$$file" "s3://$(FLOCI_S3_BUCKET)/$$key"; \
	done
	@echo "Available MCAP recordings:"
	@$(FLOCI_ENV) aws s3 ls s3://$(FLOCI_S3_BUCKET)/$(FLOCI_S3_PREFIX)/

.PHONY: list-floci-mcaps
list-floci-mcaps: start-floci
	@$(FLOCI_ENV) aws s3 ls s3://$(FLOCI_S3_BUCKET)/$(FLOCI_S3_PREFIX)/

.PHONY: stop-floci
stop-floci:
	-docker rm -f $(FLOCI_CONTAINER_NAME)

.PHONY: start-floci-gcp
start-floci-gcp:
	@docker rm -f $(FLOCI_GCP_CONTAINER_NAME) >/dev/null 2>&1 || true
	@docker run -d --name $(FLOCI_GCP_CONTAINER_NAME) -p $(FLOCI_GCP_PORT):4588 floci/floci-gcp:latest
	@echo "Waiting for Floci GCP..."
	@deadline=$$(($$(date +%s) + $(FLOCI_GCP_STARTUP_TIMEOUT_SECONDS))); \
	until curl -sf http://localhost:$(FLOCI_GCP_PORT)/_floci/health >/dev/null; do \
		if [ $$(date +%s) -ge $$deadline ]; then \
			echo "Floci GCP did not become ready within $(FLOCI_GCP_STARTUP_TIMEOUT_SECONDS) seconds"; \
			docker logs $(FLOCI_GCP_CONTAINER_NAME); \
			exit 1; \
		fi; \
		sleep 1; \
	done
	@$(FLOCI_GCP_ENV) gsutil mb gs://$(FLOCI_GCP_BUCKET) 2>/dev/null || true
	@echo "Floci GCP is ready at http://localhost:$(FLOCI_GCP_PORT)"

.PHONY: setup-floci-gcp
setup-floci-gcp: start-floci-gcp
	@for file in $(FLOCI_GCP_MCAP_FILES); do \
		key="$(FLOCI_GCP_PREFIX)/$$(basename "$$file")"; \
		echo "Uploading $$file to gs://$(FLOCI_GCP_BUCKET)/$$key..."; \
		$(FLOCI_GCP_ENV) gsutil cp "$$file" "gs://$(FLOCI_GCP_BUCKET)/$$key"; \
	done
	@echo "Available MCAP recordings:"
	@$(FLOCI_GCP_ENV) gsutil ls gs://$(FLOCI_GCP_BUCKET)/$(FLOCI_GCP_PREFIX)/

.PHONY: list-floci-gcp-mcaps
list-floci-gcp-mcaps: start-floci-gcp
	@$(FLOCI_GCP_ENV) gsutil ls gs://$(FLOCI_GCP_BUCKET)/$(FLOCI_GCP_PREFIX)/

.PHONY: stop-floci-gcp
stop-floci-gcp:
	-docker rm -f $(FLOCI_GCP_CONTAINER_NAME)

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

# Demo targets for the camera-frame endpoint.
# Uploads the MCAP to the local Floci S3 emulator and starts the API server so
# every video channel URL can be opened directly in a browser.
#
# Usage:
#   make demo-mcap-server FLOCI_MCAP_FILES=/path/to/recording.mcap
#   make demo-mcap-urls   FLOCI_MCAP_FILES=/path/to/recording.mcap   (second terminal)
DEMO_MCAP_HOST ?= 127.0.0.1
DEMO_MCAP_PORT ?= 8765
DEMO_MCAP_DB   ?= /tmp/lightly_demo_mcap.db
DEMO_DATASET_ID   := aaaaaaaa-0000-0000-0000-000000000001
DEMO_RECORDING_ID := bbbbbbbb-0000-0000-0000-000000000001
# S3 URI of the first uploaded file — derived from the floci variables above.
DEMO_MCAP_S3_URI  := s3://$(FLOCI_S3_BUCKET)/$(FLOCI_S3_PREFIX)/$(notdir $(firstword $(FLOCI_MCAP_FILES)))

.PHONY: demo-mcap-server
demo-mcap-server: setup-floci mock-webapp-dist
	@echo "Seeding database at $(DEMO_MCAP_DB) with $(DEMO_MCAP_S3_URI)..."
	@uv run python src/lightly_studio/scripts/demo_mcap_seed.py \
		"$(DEMO_MCAP_DB)" "$(DEMO_MCAP_S3_URI)" "$(DEMO_DATASET_ID)" "$(DEMO_RECORDING_ID)"
	@printf '<html><body>API demo — use the /datasets/... endpoints.</body></html>' \
		> src/lightly_studio/dist_lightly_studio_view_app/index.html
	@echo "Starting server on http://$(DEMO_MCAP_HOST):$(DEMO_MCAP_PORT) — Ctrl-C to stop"
	@$(FLOCI_ENV) uv run --extra mcap --extra cloud-storage python -c "\
import uvicorn; \
from lightly_studio.database import db_manager; \
db_manager.connect(db_file='$(DEMO_MCAP_DB)'); \
from lightly_studio.api.app import app; \
uvicorn.run(app, host='$(DEMO_MCAP_HOST)', port=$(DEMO_MCAP_PORT))"

.PHONY: demo-mcap-urls
demo-mcap-urls:
	@uv run --extra mcap python src/lightly_studio/scripts/demo_mcap_urls.py \
		"$(firstword $(FLOCI_MCAP_FILES))" "$(DEMO_MCAP_HOST)" "$(DEMO_MCAP_PORT)" \
		"$(DEMO_DATASET_ID)" "$(DEMO_RECORDING_ID)"

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

include ../make/python.mk
