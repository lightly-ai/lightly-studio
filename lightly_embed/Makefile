# The lockfile is shared with the other workspace members and lives at the repository root, so
# every uv command here resolves it from there. See ../CONTRIBUTING.md.

.PHONY: build
build:
	@echo "Building a distribution package..."
	uv build --package lightly-embed --out-dir dist

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
# install next to a customer's own CUDA and torch pins. In a monorepo that invariant is easy to
# break by accident, so it is asserted rather than reviewed. Matched as substrings, so that
# variants such as duckdb-engine, torchvision or opencv-python-headless are caught too.
FORBIDDEN_WHEEL_DEPENDENCIES := lightly-studio torch duckdb opencv
# Defaults to the floor of `requires-python`, where a marker-gated dependency is most likely to
# slip in. The unit test workflow resolves the tree once per Python it supports.
WHEEL_PYTHON_VERSION ?= 3.9

.PHONY: check-wheel-dependencies
check-wheel-dependencies: build
	@echo "Resolving the dependency tree of the built wheel..."
	@mkdir -p build
	@ls dist/lightly_embed-*.whl > build/wheel-requirements.in
	@uv pip compile build/wheel-requirements.in --python-version $(WHEEL_PYTHON_VERSION) \
		--no-header --no-annotate --quiet --output-file build/wheel-requirements.txt
	@awk -F'[=@ ]' '!/^#/ && NF && $$1 !~ /\// { print tolower($$1) }' \
		build/wheel-requirements.txt > build/wheel-dependencies.txt
	@for name in $(FORBIDDEN_WHEEL_DEPENDENCIES); do \
		if grep -q "$$name" build/wheel-dependencies.txt; then \
			echo "Error: the lightly-embed wheel resolves '$$name'. Resolved tree:"; \
			cat build/wheel-dependencies.txt; \
			exit 1; \
		fi; \
	done
	@echo "The wheel resolves none of: $(FORBIDDEN_WHEEL_DEPENDENCIES)"
