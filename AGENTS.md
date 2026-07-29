# Development Guidelines

## Coding Guidelines

**Before modifying any file, read the guidelines for its area:**
- TypeScript / frontend files → read [`ai_guidelines/frontend.md`](./ai_guidelines/frontend.md)
- Python / backend files → read [`ai_guidelines/python.md`](./ai_guidelines/python.md) and [`ai_guidelines/backend.md`](./ai_guidelines/backend.md)

All guidelines are in the `ai_guidelines` folder.

- [Best Practices](./ai_guidelines/best_practices.md): General coding principles for readability, maintainability, and performance.
- [Pull Requests](./ai_guidelines/pull_requests.md): Guidelines for submitting a pull request.
- [Frontend](./ai_guidelines/frontend.md): Architecture overview. We use TypeScript with SvelteKit.
- [Backend](./ai_guidelines/backend.md): Architecture overview. We use Python with FastAPI and SQLModel.
- [Python](./ai_guidelines/python.md): Python-specific style guidelines.
- [Glossary](./ai_guidelines/glossary.md): Terminology and naming conventions.
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
- We allow direct function imports from `tests.helpers_resolvers`, `tests.resolvers.video.helpers`, and `tests.resolvers.evaluation_sample_metric_resolver.helpers` in Python



## AI Team Workflow

For feature work, act as `lead`: read `docs/`, select the needed roles from `.agents/`, create or update a feature specification with a wireframe and decision rationale, implement only the agreed scope, then request independent validation from `quality-engineer`.
