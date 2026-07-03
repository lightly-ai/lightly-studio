# Fast Track guardrails + bot. Runs via tsx (no build artifact). Mirrors the
# lightly_studio_view toolchain (minus Svelte/Vite). See README.md.

# Wrap a command in an nvm-provisioned shell so the pinned Node (.nvmrc) is used.
define with_nvm
	bash -c 'export NVM_DIR="$${HOME}/.nvm"; \
	[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
	nvm use >/dev/null 2>&1 || nvm install; \
	$(1)'
endef

.PHONY: install
install:
	$(call with_nvm,npm ci)

.PHONY: lint
lint:
	$(call with_nvm,npm run lint)

.PHONY: static-checks
static-checks:
	$(call with_nvm,npm run static-checks)

.PHONY: format
format:
	$(call with_nvm,npm run format)

.PHONY: test
test:
	$(call with_nvm,npm run test)

# Run the guardrails against the current branch's committed changes (HEAD
# diffed vs BASE_REF, default origin/main) via tsx — the first target where the
# loop actually executes.
.PHONY: run-guardrails
run-guardrails:
	$(call with_nvm,npm run guardrails)

# Print the guardrail registry without running anything.
.PHONY: list-guardrails
list-guardrails:
	$(call with_nvm,npm run list-guardrails)
