# Install dependencies for the project
.PHONY: install
install:
ifeq ($(OS),Windows_NT)
	@echo "Checking Node.js installation..."
	@powershell -Command "if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Write-Host 'Error: Node.js is not installed. Please install Node.js >=22.11.0 from https://nodejs.org/'; exit 1 }"
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
	@powershell -Command "$$env:PUBLIC_POSTHOG_KEY='$(PUBLIC_POSTHOG_KEY)'; npm run build"
else
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm install; \
	nvm use; \
	PUBLIC_POSTHOG_KEY=$${PUBLIC_POSTHOG_KEY} npm run build'
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
