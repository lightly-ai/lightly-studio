# CI-internal release tooling. Kept out of the workspace's uv project on purpose
# (`--no-project`): it must run before, and independently of, the LightlyStudio
# environment it prepares a release for.
UV := uv run --no-project

.PHONY: static-checks
static-checks: format-check lint type-check

.PHONY: format-check
format-check:
	$(UV) --with ruff ruff format --check .

.PHONY: lint
lint:
	$(UV) --with ruff ruff check .

.PHONY: type-check
type-check:
	$(UV) --with mypy mypy prepare_release

.PHONY: format
format:
	$(UV) --with ruff ruff format .

.PHONY: test
test:
	$(UV) --with pytest pytest -q
