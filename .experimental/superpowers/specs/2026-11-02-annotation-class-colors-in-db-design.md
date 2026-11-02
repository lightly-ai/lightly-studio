# Annotation class colors in the DB (LIG-11355)

Builds on `michal-lig-11319-annotation-classes-tab-ui`.

## Why

A customer wants custom class colors shared by all users of a dataset. Today they live in
browser memory and are lost on reload.

## Decision: per dataset, not per user

- User info is not currently available at the backend.
- Per-user overrides can be added later, once the backend knows the user.

## What the user gets

- A class color set in the legend or the Annotation Classes tab is saved for the dataset.
- "Reset to default" in the color picker restores the default color.

## How

**Backend**
- Nullable `color` and `alpha` on `annotation_label`. Null means default color.
- Endpoint to set or clear a class color. A rename must not clear the color.
- Alembic migration. Existing DuckDB files are not upgraded (as in #2782); add a CHANGELOG note.

**Frontend**
- Separate class and source color lookups: `getColorByLabel` for classes, a new
  `getColorBySource` for sources. Call sites that color by source call the latter.
- Load class colors from the class list. Colors are keyed by class ID, so renames keep them.
  Drop the rename workaround in `useAnnotationClasses`.
- Live preview is a local layer on top of saved colors, so a refetch does not drop it.
  Apply saves, Cancel discards. On save error: toast and revert.

## Out of scope

- Annotation source colors (color-by-source mode) stay browser-only.
- Live updates from other users; colors refresh when the class list refetches.
- Export/import of colors.
