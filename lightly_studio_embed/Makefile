include ../make/python.mk

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

# The dependency tree of the published wheel is the whole point of this package: it has to
# install next to a customer's own CUDA and torch pins. The check lives in Python rather than in
# shell so that it runs the same way on every platform; the forbidden set is in that script.
WHEEL_PYTHON_VERSION ?= 3.9

.PHONY: check-wheel-dependencies
check-wheel-dependencies: build
	uv run scripts/check_wheel_dependencies.py --python-version $(WHEEL_PYTHON_VERSION)
