---
name: adding-analytics-events
description: Read when a change adds or changes something a user does in LightlyStudio, in the GUI, the Python SDK, or the CLI, for example creating, editing, deleting, relabeling, tagging, exporting, importing, or starting a run. Explains which actions need a PostHog event, which layer fires it (frontend hook or SDK/CLI method, never services or resolvers), how to name it, which properties are safe to send, and how to test it.
---

# Adding analytics events

Each user action that a PR adds or changes fires one PostHog event in the same PR.
Without the event, the team cannot see if people use the feature.

## Decide if the change needs an event

An action changes data or starts work: create, edit, delete, relabel, move, or tag data; export
or download; import; start a compute or model run; submit a dialog; open a new tool.

A new way to do an existing action (a keyboard shortcut, a new SDK input class) does not get a
new event. Add a property to the existing event, for example `trigger: 'keyboard'`, so one event
still counts every use of the action.

Read-only queries, hover states, visual toggles, layout changes, and refactors need no event.

## Find the layer that fires it

Follow the call path from the user's click or SDK call down to the database before you write
code. The GUI and the SDK both call the services and resolvers, so do not fire events there.
Fire at the entry point:

- **GUI:** in the mutation hook after `mutateAsync` resolves, or in the handler after the action
  succeeds.
- **SDK and CLI:** in the public method or CLI command, after it succeeds. The SDK has no UI, so
  each public method that changes data needs its own event.

If a layer on the path already fires an event for the action, do not add another one.

## Fire it

Frontend: `usePostHog` from `$lib/hooks`. The model is
`lightly_studio_view/src/lib/hooks/useDeleteAnnotation/useDeleteAnnotation.ts`:

```ts
const { trackEvent } = usePostHog();
// ...
await mutation.mutateAsync({ path: { collection_id: collectionId, annotation_id: annotationId } });
trackEvent('annotation_deleted', { collection_id: collectionId, annotation_type: annotationType });
```

Python: `tracking.track(event=..., properties=...)` from `lightly_studio.analytics`. Add the event
name as a constant in `lightly_studio/src/lightly_studio/analytics/tracking.py`, next to
`APP_LAUNCHED`, and send `"source": "sdk"`. `track` never raises, so do not wrap it in
`try`/`except`.

## Name it and pick properties

- **Name:** snake_case, `<object>_<past tense verb>`, such as `annotation_deleted` or
  `export_triggered`. Reuse an existing name if one fits. To list the names in use, run
  `grep -rhoE "trackEvent\('[a-z_]+'" lightly_studio_view/src | sort -u` and read the constants
  in `analytics/tracking.py`.
- **Properties:** IDs, counts, types, enums, booleans. Never emails, names, file paths, class
  names, tag names, captions, or other text that a user typed. Tracking is anonymous, and such
  text can hold personal or customer data.
- Fire once per action, after success. Not per item, not on error or cancel. For a bulk action,
  send one event with a count.

## Test it

Assert the event name and properties.

- **vitest:** mock `usePostHog` and keep the rest of `$lib/hooks`:

  ```ts
  const { trackEvent } = vi.hoisted(() => ({ trackEvent: vi.fn() }));
  vi.mock('$lib/hooks', async (importOriginal) => ({
      ...((await importOriginal()) as object),
      usePostHog: () => ({ trackEvent })
  }));
  ```

- **pytest:** `mocker.patch.object(tracking, "track")`, then
  `assert_called_once_with(event=..., properties=...)`. See `lightly_studio/tests/test_cli.py`.

## Before you report done

- Each new or changed action fires one event, or adds a property to an existing event.
- The event fires once, after success, from the frontend hook or the SDK/CLI method.
- No property holds user-typed text, names, or paths.
- A test asserts the event name and properties.

## Ask the user first

- Before you rename or remove an existing event or property. Dashboards and insights in
  PostHog depend on these names.
- When you cannot tell if an action needs an event.
