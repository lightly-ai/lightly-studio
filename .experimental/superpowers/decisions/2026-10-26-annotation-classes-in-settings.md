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
2. Class pickers no longer offer "Create". They have a button that opens the settings. It does not
   offer to add the typed name, so labelers are not led to create classes.
3. Saving an annotation never creates a class. This includes Smart select and Find all instances:
   they use a matching existing class, or ask the user to pick one.
4. No access control yet. Anyone can still add classes in the settings. Roles come later.
5. In the settings tab, one field finds or adds a class. Enter adds a class only when no class
   matches, so a search such as "bea" for "bear" does not add a class.
6. Each class shows its color, which the user can change, and its number of annotations. A new
   class is highlighted and scrolled into view, so the user can change it immediately.
7. Deleting a class also deletes its annotations. A modal asks for confirmation and shows how many
   annotations it deletes.
8. A class belongs to the dataset. Its annotation count includes all annotations of the class in
   the dataset, of all annotation and sample types, so it matches what a delete removes.

## Open questions

1. Custom colors are kept only in the browser memory, by class name. They are lost on reload and
   other users do not see them. Without a custom color, renaming a class changes its color. Should
   the color be stored with the class in the backend?
2. Separate tab, or a section in the Annotations tab?
3. Adding annotations from Python, for example from COCO, still creates classes. Keep that?
4. How does a user with a new, empty dataset learn to add classes first?
