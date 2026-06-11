### Documentation

# Build docs for the current version.
# `--strict` turns the validation warnings configured in mkdocs.yml (broken
# anchors/links, pages missing from nav) into build errors.
.PHONY: docs
docs:
	@echo "📚 Building documentation..."
	uv run --group=docs mkdocs build --clean --strict

.PHONY: serve
serve:
	@echo "📚 Building documentation..."
	uv run --group=docs mkdocs serve
