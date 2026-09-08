.PHONY: clean
clean:
ifeq ($(OS),Windows_NT)
	@powershell -Command "if (Test-Path dist) { Remove-Item -Path dist -Recurse -Force }"
else
	rm -rf dist
endif

# Cleans first, so that the wheel glob in check-wheel-dependencies below can only ever match
# the artifact this build produced.
.PHONY: build
build: clean
	@echo "Building a distribution package..."
	uv build --package lightly-studio-embed --out-dir dist

.PHONY: test
test:
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

# The dependency tree of the published wheel is the whole point of this package: it has to
# install next to a customer's own CUDA and torch pins. The check lives in Python rather than in
# shell so that it runs the same way on every platform; the forbidden set is in that script.
WHEEL_PYTHON_VERSION ?= 3.9

.PHONY: check-wheel-dependencies
check-wheel-dependencies: build
	uv run scripts/check_wheel_dependencies.py --python-version $(WHEEL_PYTHON_VERSION)
