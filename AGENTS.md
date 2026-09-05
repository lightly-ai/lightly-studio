# Development Guidelines

## Coding Guidelines

Our coding guidelines are [Agent Skills](https://agentskills.io) in [`.agents/skills`](./.agents/skills).
Skills do not load automatically. Before you edit a file, load the skill for its path. If your
tool cannot load skills, read that `SKILL.md` first.

Load the skill that matches the path you edit:

- `lightly_studio/**/*.py`, `lightly_embed/**/*.py` → [python-guide](./.agents/skills/python-guide/SKILL.md): Python style.
- `lightly_studio/src/lightly_studio/**` → also [backend-guide](./.agents/skills/backend-guide/SKILL.md): FastAPI and SQLModel.
- `lightly_studio_view/**` (`.ts`, `.svelte`) → [frontend-guide](./.agents/skills/frontend-guide/SKILL.md): TypeScript and SvelteKit.

When the task matches, also load:

- [best-practices](./.agents/skills/best-practices/SKILL.md): a new function, module, or component.
- [glossary](./.agents/skills/glossary/SKILL.md): names for anything that users see.
- [pull-requests](./.agents/skills/pull-requests/SKILL.md): a pull request.
- [Contributing](./CONTRIBUTING.md): setup and tests.

Claude Code gives you a reminder. A `PreToolUse` hook (`.claude/settings.json` and
`.claude/hooks/skill-reminder.py`) shows the matching skill when you edit these paths.

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
