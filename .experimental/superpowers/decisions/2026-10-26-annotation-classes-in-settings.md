# Decision record: annotation classes are defined in the settings

- Date: 2026-10-26
- Issue: LIG-11319
- Status: prototype, for team review
- Prototype branch: `michal-lig-11319-annotation-classes-in-settings-prototype`

## Context

Today, anyone who edits annotations in the detail view can create a new annotation class. They
type a name in a class picker and select "Create: <name>". Some tools also create a missing class
when they save an annotation.

LightlyStudio Enterprise can run with many users. Admins define the annotation classes. Labelers
must only pick from that list. Today a labeler can add a stray class, and someone must delete it
later. We want to prevent this, and not depend on admins and labelers talking to each other.

Findings from the codebase at the time of this record:

- An annotation class belongs to a dataset. Its name is unique in that dataset.
- One shared picker (`SelectList`) shows the "Create" option. About eight class pickers use it.
- These save paths create a missing class: the bounding box tool, the segmentation brush,
  classification, video, 3D cuboids, Smart select and Find all instances.
- The settings dialog only has personal preferences (shortcuts, display, annotations).
- The backend can already add, rename and delete annotation classes.
- LightlyStudio has no roles or permissions. The enterprise code only connects to a shared
  database.

## Decisions

Decisions by the team:

1. **Annotation classes are created only in the settings.** This is true for all users and all
   setups, not only for Enterprise.
2. **The detail view gets a button that opens the settings.**
3. **The settings get a new tab next to the Annotations tab.**
4. **The first version has no real enforcement.** Anyone who can open the settings can still add a
   class. Roles and permissions come later.
5. **Smart select and Find all instances only use existing classes.** If the selected class, the
   typed prompt or the model suggestion matches an existing class, ignoring case and outer spaces,
   that class is used. If nothing matches, nothing is saved and the user picks an existing class.
   The Find all instances prompt is a search text. It never becomes a class name.
6. **Start with a throwaway prototype in the real app, frontend only.** Colleagues review it and
   decide if the decisions above need changes.

Calls made while building the prototype (not yet agreed by the team):

- The tab is called "Annotation classes", following the glossary. The picker button is called
  "Edit annotation classes".
- The tab saves each change immediately. It does not use the "Save changes" button of the
  settings dialog.
- The tab shows the classes of the dataset in the current page. Outside a dataset it shows a
  message.
- Tag pickers and annotation source pickers can still create new entries.
- When a tool saves with a class that no longer exists, for example a deleted class that the tool
  remembered, it shows an error message with an "Open settings" button.
- The bulk classification class picker also stops creating classes.

## Consequences

- Labelers can no longer create classes by mistake while labeling.
- An admin must add classes before labeling starts. A new dataset without annotations has no
  classes, so the pickers are empty until someone adds classes in the settings.
- Moving the button is not access control. A labeler can still add a class in the settings.

## Open questions for the review

1. **Deleting a class that annotations use.** The database refuses it, and the prototype shows
   "Annotations of this class must be deleted first." Options: block it (current), also delete the
   annotations, or hide the delete button for classes in use.
2. **Where the tab lives.** A separate tab, or a section in the Annotations tab.
3. **Python API.** Adding annotations from Python, for example from COCO, still creates classes.
   Should that stay?
4. **Enforcement.** When and how admins and labelers get different rights.
5. **First-run experience.** How a user with a new dataset learns that they must add classes first.

## Prototype limits

- Not production code. Existing unit tests that expect the "Create" option fail, and there are no
  new tests.
- `useCreateLabel` keeps its name but only looks up existing classes.
- Error handling is minimal.
