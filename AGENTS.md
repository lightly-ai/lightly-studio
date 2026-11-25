# Development Guidelines

## Coding Guidelines

Our coding guidelines are [Agent Skills](https://agentskills.io) in [`.agents/skills`](./.agents/skills).
Skills do not load automatically. Before you edit a file, load the skill for its path. If your
tool cannot load skills, read that `SKILL.md` first.

Load the skill that matches the path you edit:

- `lightly_studio/**/*.py`, `lightly_studio_serve/**/*.py` → [python-guide](./.agents/skills/python-guide/SKILL.md): Python style.
- `lightly_studio/src/lightly_studio/**` → also [backend-guide](./.agents/skills/backend-guide/SKILL.md): FastAPI and SQLModel.
- `lightly_studio_view/**` (`.ts`, `.svelte`) → [frontend-guide](./.agents/skills/frontend-guide/SKILL.md): TypeScript and SvelteKit.
- Each `.py`, `.ts`, and `.svelte` file in the repository → also [clean-code](./.agents/skills/clean-code/SKILL.md): names, function shape, errors, comments.
- `CHANGELOG.md`, `lightly_studio_serve/CHANGELOG.md` → [changelog](./.agents/skills/changelog/SKILL.md): changelog entries.

When the task matches, also load:

- [glossary](./.agents/skills/glossary/SKILL.md): names for anything that users see.
- [pull-requests](./.agents/skills/pull-requests/SKILL.md): a pull request.
- [Contributing](./CONTRIBUTING.md): setup and tests.

Claude Code gives you a reminder. A `PreToolUse` hook (`.claude/settings.json` and
`.claude/hooks/skill-reminder.py`) shows the matching skill when you edit these paths.

## Product Analytics

Each user action that a PR adds or changes fires one PostHog event in the same PR.

- **Actions:** create, edit, delete, relabel, move, or tag data; export or download; import;
  start a compute or model run; submit a dialog; open a new tool. A new way to do an existing
  action (a keyboard shortcut, a new SDK input class) also counts: add a property to the
  existing event, for example `trigger: 'keyboard'`.
- **No event for:** read-only queries, hover states, visual toggles, layout changes, refactors.
- **Frontend:** `const { trackEvent } = usePostHog();` from `$lib/hooks`. Fire in the mutation
  hook after `mutateAsync` resolves, or in the handler after the action succeeds. Ref:
  `lightly_studio_view/src/lib/hooks/useDeleteAnnotation/useDeleteAnnotation.ts`.
- **Python SDK and CLI:** `tracking.track(event=..., properties=...)` from
  `lightly_studio.analytics`, in the public method or CLI command, after it succeeds. Add the
  event name as a constant in `analytics/tracking.py` and send `"source": "sdk"`. The SDK has
  no UI, so each public method that changes data needs its own event.
- Do not fire events in services or resolvers: the GUI and the SDK both call them. Follow the
  call path first. If a layer already fires an event for the action, do not add another one.
- **Names:** snake_case, `<object>_<past tense verb>`, such as `annotation_deleted` or
  `export_triggered`. Reuse an existing name if one fits.
- **Properties:** IDs, counts, types, enums, booleans. Never emails, names, file paths, class
  names, tag names, captions, or other text that a user typed.
- Fire once per action, after success. Not per item, not on error or cancel.
- Add a test that asserts the event fires: mock `usePostHog` in vitest, or use
  `mocker.patch.object(tracking, "track")` in pytest (see `lightly_studio/tests/test_cli.py`).

## Validation

### Backend

```
cd lightly_studio
make static-checks
uv run pytest <affected_tests>
```

Run `make test` for the full testsuite, use sparingly. The tests need only a mock webapp, which
`make test` creates. To build the real frontend, run `make build-lightly_studio_view`. It takes
several minutes, avoid if not needed.

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

## Superpowers

Save superpowers docs under `.experimental/superpowers/` instead of `docs/superpowers/`.
