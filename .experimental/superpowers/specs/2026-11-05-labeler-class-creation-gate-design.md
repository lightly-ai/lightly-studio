# Only editors create annotation classes (LIG-11356)

## Why

The annotation classes define what a dataset is labeled with. Labelers should label with
these classes, not change them. Today a labeler can add a class from any class picker.

We gate this in the frontend only. The backend does not know the user role yet. When it does,
it will enforce the rule too.

## What changes

Users below the editor role (labelers and viewers) can only pick existing classes. Editors,
admins and local mode (no role) see no change.

## How

**Role rule.** One hook, `useCanCreateAnnotationClass()`, holds the rule
(`hasMinimumRole(user?.role, 'editor')`). The pickers and the save guard both use it.

**Class pickers.** A new opt-in `SelectList` prop hides the "Create: …" row and stops Enter
from creating the typed name. Every class picker sets it from the hook and drops "or create"
from its text. When a search finds nothing, the picker says *No class found.* The pickers:

- `AnnotationClassSelect` (drawing tools, SAM3, smart select)
- `SelectClassDialog` (also the point cloud workspace)
- `FrameAnnotationsPanel`
- `AnnotationMetadataLabel`, `SampleDetailsSidePanelAnnotation` (relabel)
- `SampleDetailsClassificationSegment` (both pickers)
- `PointCloudAnnotationLabel`
- `AnnotationsGrid/SelectedAnnotations` (bulk relabel)
- `BulkClassificationPanel`, class field only

**Save guard.** The app remembers the last picked class. If an editor deletes it, a labeler
can create it again by saving. To stop this, `useCreateLabel` checks the role:

- Below editor, it sends no request.
- It rejects with an error. The error text is *Class "X" is no longer available. Choose
  another class.* This stops the save.
- It shows no message. The caller shows it, as callers already do for other errors.

Callers that show a fixed message (*…Please try again.*) show the error text for this error
instead. Callers that already show the error text need no change.

Two callers need more:

- The mask brush trims overlapping masks before it creates the class. It must stop first if
  the class is missing and the user cannot create it, so other masks stay untouched.
- `SampleDetailsClassificationSegment` calls `createLabel` outside its `try`. Move it inside.

**Later.** The app should forget the remembered class when someone deletes it. Then saves
would not use a deleted class at all. This is a separate ticket.

**Known gap.** Bulk classification, relabel, bulk relabel and relabel undo send a class name.
The backend creates the class if it is missing. So a labeler can still bring back a deleted
class through these paths. Backend role checks will close this.

## Unchanged

- **Settings:** already editor-only.
- **SAM3 prompt:** stays free text. It is a search phrase, not a class name.

## Out of scope

Backend checks, annotation sources, tags, captions.

## Left to the builder

Prop name, and tests for the hook, the `SelectList` prop, one picker, and the save guard.
