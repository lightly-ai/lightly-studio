# AI Assistant Instructions

When working on the LightlyStudio codebase, always follow these coding guidelines:

## Coding Guidelines
- **For Pull Requests**: [./pull_requests.md](./pull_requests.md)
- **Best Practices**: [./best_practices.md](./best_practices.md)
- **Frontend** (SvelteKit/TypeScript): [./frontend.md](./frontend.md)
- **Backend** (Python): [./backend.md](./backend.md)
- **Contributing**: [../CONTRIBUTING.md](../CONTRIBUTING.md)

## Key Frontend Reminders
- Use `$app/state` instead of `$app/stores` for accessing page state
- Use Svelte 5 event syntax (`onclick`, `onchange`) instead of Svelte 4 syntax (`on:click`, `on:change`)
- Avoid Svelte 4 reactive syntax (`$:`), use `$derived` rune or derived stores instead
- Don't mix `derived` from `svelte/store` with `$derived` rune syntax
- Keep components under 100 lines - split into smaller components if needed
- Use absolute imports with `$lib/` prefix
- Prefer Svelte stores (`writable`, `readable`, `derived`) over runes for state management
- Use TypeScript utility types instead of exporting/importing types
- Write tests for new code using vitest
- Use the hook design pattern for reusable logic in `src/lib/hooks`

## Key Backend Reminders
- Follow Python best practices and type hints
- Write tests for new functionality
- Use appropriate error handling

## Testing
- Write unit tests for components and functions
- Write integration tests for component interactions
- Run `make static-checks` and `make test` before submitting PRs

## Development Workflow
- Backend: `cd lightly_studio && make start`
- Frontend: `cd lightly_studio_view && npm run dev`
- Tests: Run `make test` in respective directories

Before making any code changes, review the appropriate guidelines to ensure your approach aligns with the project's standards.
