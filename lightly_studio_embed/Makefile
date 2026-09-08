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
	uv build --package lightly-studio-embed --out-dir dist

# Exit code 5 is "no tests collected", which is the honest state until serve() adds code and
# tests of its own. Any real failure still fails the target.
.PHONY: test
test:
	@echo "Running tests..."
	uv run pytest || [ $$? -eq 5 ]

include ../make/python.mk
