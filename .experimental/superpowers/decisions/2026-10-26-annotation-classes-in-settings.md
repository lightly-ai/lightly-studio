# Decision record: annotation classes are defined in the settings

LIG-11319 · 2026-10-26 · Prototype for team review on branch
`michal-lig-11319-annotation-classes-in-settings-prototype`

## Why

With Enterprise, many users share a dataset. Admins define the annotation classes, and labelers
must only pick from them. Today anyone can create a class while labeling, so stray classes appear
and someone must clean them up.

## Decisions

1. Annotation classes are created only in the settings, in a new tab next to Annotations. This
   applies to everyone, not only Enterprise.
2. Class pickers no longer offer "Create". They have a button that opens the settings.
3. Saving an annotation never creates a class. This includes Smart select and Find all instances:
   they use a matching existing class, or ask the user to pick one.
4. No access control yet. Anyone can still add classes in the settings. Roles come later.

## Open questions

1. Deleting a class that annotations use fails. Should we block it, delete the annotations too, or
   hide the button?
2. Separate tab, or a section in the Annotations tab?
3. Adding annotations from Python, for example from COCO, still creates classes. Keep that?
4. How does a user with a new, empty dataset learn to add classes first?
