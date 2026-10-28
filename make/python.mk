# Targets shared by every Python workspace member. Each member includes this file rather than
# copying the commands, so a new sibling package gets them for free and they cannot drift.
#
# Members add what is genuinely theirs on top: `build`, `test`, and anything package specific.

# Members can set uv dependency-group flags for their own environment.
UV_GROUP_FLAGS ?=

.PHONY: check-uv-lock
check-uv-lock:
	@echo "Ensuring uv.lock is up to date..."
	uv lock --check

.PHONY: lint
lint:
	@echo "Linting project with ruff..."
	uv run $(UV_GROUP_FLAGS) ruff check

.PHONY: type-check
type-check:
	@echo "Checking types with mypy..."
	uv run $(UV_GROUP_FLAGS) mypy .

.PHONY: format-check
format-check:
	@echo "Checking format with ruff..."
	uv run $(UV_GROUP_FLAGS) ruff format --check

.PHONY: static-checks
static-checks: check-uv-lock lint type-check format-check

.PHONY: format
format:
	@echo "Formatting project with ruff..."
	uv run $(UV_GROUP_FLAGS) ruff format
	uv run $(UV_GROUP_FLAGS) ruff check --fix

.PHONY: lint-fix
lint-fix:
	uv run $(UV_GROUP_FLAGS) ruff check --fix
