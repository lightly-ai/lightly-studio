# Development Guidelines

## Coding Guidelines

Guidelines are stored in the `ai_guidelines` folder.

- [Best Practices](./ai_guidelines/best_practices.md): General coding principles for readability, maintainability, and performance.
- [Pull Requests](./ai_guidelines/pull_requests.md): Guidelines for submitting a pull request.
- [Frontend](./ai_guidelines/frontend.md): Architecture overview. We use TypeScript with SvelteKit.
- [Backend](./ai_guidelines/backend.md): Architecture overview. We use Python with FastAPI and SQLModel.
- [Python](./ai_guidelines/python.md): Python-specific style guidelines.
- [Contributing](./CONTRIBUTING.md): Contribution guidelines, including development setup and testing instructions.

## Validation

### Backend

```
cd lightly_studio
make static-checks
make test
```

Read `lightly_studio/Makefile` for detailed commands.

### Frontend

```
cd lightly_studio_view
make static-checks
make test
```

Read `lightly_studio_view/Makefile` and `lightly_studio_view/package.json` for detailed commands.

## Review Guidelines

- For Codex: Focus on code style during code review. Make the code style comments priority P2,
and make as many of them as necessary. Use succinct language in the comments.
- Make sure the PR follows guidelines in the `ai_guidelines` folder.

Exceptions from the guidelines:
- We allow direct function imports from `tests.helpers_resolvers` and `tests.resolvers.video.helpers` in Python


