# Install dependencies for the project
.PHONY: install
install:
ifeq ($(OS),Windows_NT)
	@echo "Checking Node.js installation..."
	@powershell -Command "if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Write-Host 'Error: Node.js is not installed. Please install Node.js >=22.11.0 from https://nodejs.org/'; exit 1 }"
	npm ci
else ifeq ($(CI),true)
# CI installs Node with actions/setup-node from the same .nvmrc, so there is nothing
# left for nvm to do. Skipping it also keeps a remote installer out of the build,
# which matters once a workflow builds the wheel in a job that can publish it.
	npm ci
else
	curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm install; \
	nvm use; \
	npm ci;'
endif

.PHONY: build
build: install
ifeq ($(OS),Windows_NT)
	npm run build
else
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm install; \
	nvm use; \
	npm run build'
endif

# Fast build: skips npm ci, nvm install, and langium generate.
# Assumes node_modules and generated language files are up to date.
.PHONY: build-dirty
build-dirty:
ifeq ($(OS),Windows_NT)
	npm run build-dirty
else
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm use; \
		npm run build-dirty'
endif

# Reinstall only when dependencies are missing or the lockfile or Node version
# changed. The marker is written after a successful npm ci.
.PHONY: install-if-needed
install-if-needed:
ifeq ($(OS),Windows_NT)
	@powershell -Command "$$signature = (Get-FileHash package.json, package-lock.json -Algorithm SHA256 | ForEach-Object Hash) -join ':'; $$signature += ':' + (node --version); $$marker = 'node_modules/.lightly-studio-deps-signature'; if ((Test-Path node_modules) -and (Test-Path $$marker) -and ((Get-Content $$marker -Raw).Trim() -eq $$signature)) { Write-Host 'Frontend dependencies are up to date.' } else { npm ci; if ($$LASTEXITCODE -ne 0) { exit $$LASTEXITCODE }; New-Item -ItemType Directory -Force node_modules | Out-Null; Set-Content -NoNewline $$marker $$signature }"
else
	bash -c 'set -e; \
	export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm use; \
	marker=node_modules/.lightly-studio-deps-signature; \
	signature=$$(shasum -a 256 package.json package-lock.json | shasum -a 256 | awk "{print \$$1}"):$$(node --version); \
	if [ -d node_modules ] && [ -f "$$marker" ] && [ "$$(cat "$$marker")" = "$$signature" ]; then \
		echo "Frontend dependencies are up to date."; \
	else \
		npm ci; \
		mkdir -p node_modules; \
		printf "%s\\n" "$$signature" > "$$marker"; \
	fi'
endif

.PHONY: build-cached
build-cached: install-if-needed
ifeq ($(OS),Windows_NT)
	npm run build-dirty
else
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm use; \
	npm run build-dirty'
endif

.PHONY: static-checks
static-checks:
ifeq ($(OS),Windows_NT)
	npm run static-checks
else
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm use; \
	npm run static-checks'
endif

.PHONY: format
format:
ifeq ($(OS),Windows_NT)
	npm run format
else
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm use; \
	npm run format'
endif

.PHONY: test
test:
ifeq ($(OS),Windows_NT)
	npm run test:unit -- --run
else
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm use; \
	npm run test:unit -- --run'
endif

# Full-suite line coverage for the Fast Track coverage guardrail, which reads
# coverage/coverage-final.json rather than running tests itself.
.PHONY: test-coverage
test-coverage:
ifeq ($(OS),Windows_NT)
	npm run test:unit -- --run --coverage --coverage.reporter=json --coverage.reportOnFailure
else
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm use; \
	npm run test:unit -- --run --coverage --coverage.reporter=json --coverage.reportOnFailure'
endif
