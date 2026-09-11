.PHONY: clean
clean:
ifeq ($(OS),Windows_NT)
	@powershell -Command "if (Test-Path dist) { Remove-Item -Path dist -Recurse -Force }"
else
	rm -rf dist
endif

# Cleans first, so that dist/ only ever holds the artifact this build produced.
.PHONY: build
build: clean
	@echo "Building a distribution package..."
	uv build --package lightly-studio-serve --out-dir dist

# The wheel is installed next to a customer's own CUDA and torch pins, so it must stay light.
# Resolved from the built wheel rather than read from pyproject.toml, because the dependency
# that would break that arrives one level down. The release workflow runs the same check
# before it publishes anything.
.PHONY: check-wheel-dependencies
check-wheel-dependencies: build
	@echo "Checking the wheel's resolved dependencies..."
	PYTHONPATH=../.github/scripts python3 -m prepare_release check-wheel-dependencies \
		--package lightly-studio-serve --dist dist

.PHONY: test
test:
	@echo "Running tests..."
	uv run pytest

include ../make/python.mk
