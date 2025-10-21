# Install dependencies for the project
.PHONY: install
install:
	curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm install; \
	nvm use; \
	npm ci;'

.PHONY: build
build: install
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm install; \
	nvm use; \
	PUBLIC_POSTHOG_KEY=$${PUBLIC_POSTHOG_KEY} npm run build'

.PHONY: static-checks
static-checks:
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm use; \
	npm run static-checks'

.PHONY: format
format:
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm use; \
	npm run format'

.PHONY: test
test:
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm use; \
	npm run test:unit -- --run'
