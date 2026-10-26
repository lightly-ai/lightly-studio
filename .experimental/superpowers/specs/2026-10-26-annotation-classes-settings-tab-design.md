# Design: annotation classes tab in the settings

LIG-11319 · 2026-10-26 · Prototype: branch `michal-lig-11319-annotation-classes-in-settings-prototype`

## Why

On shared Enterprise datasets, admins should define the annotation classes and labelers should
only pick from them. Today anyone can create a class while labeling, so stray classes appear.
This first step adds a settings tab to manage classes. Unlike the prototype, it keeps class
creation in the labeling flow.

## Scope

In: a new "Annotation classes" settings tab to add, find, rename, recolor, and delete the classes
of the current dataset, with an annotation count per class.

Out (no change, or a follow-up):
- Class pickers, Smart select, Find all instances. They keep working for every user.
- Role checks. A follow-up blocks the labeler role from creating classes outside the tab.
- Storing colors in the database.
- Tags and annotation sources.

## Behavior

1. **Find or add.** One field filters the list. Enter adds a class only when no class matches, so
   typing "bea" while "bear" exists never adds "bea".
2. **Rows.** Name (rename inline), color (color picker), annotation count, delete. A new class is
   highlighted and scrolled into view. A duplicate name shows an error.
3. **Counts** cover all annotations of the class in the dataset, across all sample and annotation
   types, so they match what a delete removes.
4. **Delete** asks for confirmation. The modal shows the number of annotations that will be
   deleted and warns that the evaluation runs that use them become stale.
5. **Colors** stay in browser memory by class name (`useCustomLabelColors`). A rename moves the
   color. Colors are lost on reload and are not shared.
6. Changes apply at once, not on the dialog's "Save changes" *(my call, as in the prototype)*.
   They refresh every class list in the app. A delete invalidates all cached data.

## Backend

- New `GET /collections/{collection_id}/annotation_labels_with_counts`: the classes of the
  dataset with `annotation_count`.
- `DELETE /annotation_labels/{label_id}` also deletes the class's annotations. Today it deletes
  only the class row, so it fails on the annotations' foreign key for any class in use. It returns
  404 before it deletes anything if the class does not exist. No current caller depends on the old
  behavior.
- The delete matches the bulk annotation delete (`_delete_annotations` in
  `bulk_delete_annotations.py`): it marks the evaluation runs of the affected collections stale.
  It deletes no runs and no per-class metric rows. *(My call: share that logic, do not copy it.)*

## Delivery

Two PRs: the backend with tests and the regenerated API client, then the frontend tab.

## Left to the builder

- What to reuse from the prototype. Its tab, `useAnnotationClasses`, delete dialog, and color
  picker fix for modals are a starting point. Its picker changes are out of scope.
- Layout, wording (see the glossary skill), error messages, and empty states.
