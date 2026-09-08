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

# Exit code 5 is "no tests collected". The package has no code to test yet, and any real
# failure still fails the target.
# TODO(Iunir, 09/2026): Drop the exit code 5 tolerance once the package has tests.
.PHONY: test
test:
	@echo "Running tests..."
	uv run pytest || [ $$? -eq 5 ]

include ../make/python.mk
