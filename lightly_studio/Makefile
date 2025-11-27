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
build-lightly_studio_view: export-schema
	PUBLIC_POSTHOG_KEY=$(PUBLIC_POSTHOG_KEY) make -C ../lightly_studio_view build
	cp -r ../lightly_studio_view/build/ src/lightly_studio/dist_lightly_studio_view_app

.PHONY: start
start: build
	$(MAKE) start-example

.PHONY: start-e2e
start-e2e: build
	@echo "Starting server for e2e tests..."
	uv run e2e-tests/index_dataset_for_end2end_ui_tests.py

.PHONY: start-coco-10k
start-coco-10k: build
	@echo "Starting server for e2e tests with COCO 10k dataset..."
	uv run e2e-tests/index_coco_10k.py

.PHONY: start-e2e-with-captions
start-e2e-with-captions: build
	@echo "Starting server for e2e tests with captions..."
	uv run e2e-tests/index_with_captions.py

# Note: we just mock dist_lightly_studio_view_app folder to avoid failing exporting the schema
# because we need to have schema before building the frontend app
.PHONY: export-schema
export-schema:
	mkdir -p src/lightly_studio/dist_lightly_studio_view_app
	touch src/lightly_studio/dist_lightly_studio_view_app/index.html
	@echo "Exporting schema for API..."
	uv run src/lightly_studio/export_schema.py
	rm -rf src/lightly_studio/dist_lightly_studio_view_app

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
	rm -rf *.db
	rm -rf *.db.wal
	rm -rf dist/*
	rm -rf src/lightly_studio/dist_lightly_studio_view_app
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.egg-info" -type d -exec rm -rf {} +
