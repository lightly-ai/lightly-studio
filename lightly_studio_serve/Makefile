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

.PHONY: test
test:
	@echo "Running tests..."
	uv run pytest

include ../make/python.mk
