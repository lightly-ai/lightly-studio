# Development Guidelines

## Coding Guidelines

Our coding guidelines are [Agent Skills](https://agentskills.io) in [`.agents/skills`](./.agents/skills).
Claude Code, Codex and Gemini CLI load them automatically when a task matches. If your tool does not
support skills, read the relevant `SKILL.md` yourself before changing code:

- [Frontend](./.agents/skills/frontend-guide/SKILL.md): TypeScript and SvelteKit standards. Read before touching `lightly_studio_view`.
- [Python](./.agents/skills/python-guide/SKILL.md): Python style. Read before touching any Python file.
- [Backend](./.agents/skills/backend-guide/SKILL.md): FastAPI and SQLModel architecture. Read before touching `lightly_studio`.
- [Best Practices](./.agents/skills/best-practices/SKILL.md): General principles for readability, maintainability, and performance.
- [Glossary](./.agents/skills/glossary/SKILL.md): Terminology and naming conventions.
- [Pull Requests](./.agents/skills/pull-requests/SKILL.md): Guidelines for submitting a pull request.
- [Contributing](./CONTRIBUTING.md): Development setup and testing instructions.

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
- Make sure the PR follows our coding guidelines.

Exceptions from the guidelines:
- We allow direct function imports from `tests.helpers_resolvers`, `tests.resolvers.video.helpers`, and `tests.resolvers.evaluation_sample_metric_resolver.helpers` in Python
