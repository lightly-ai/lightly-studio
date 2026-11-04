# Annotation Card and Target Chip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `SelectedBoxPanel` with an annotation card at the selected box or mask, add a
source and class chip by the toolbar, and stop any new annotation from getting a silent class or
source.

**Architecture:** Pure helpers (placement, key guards, matching, recent list) carry the logic and
the tests. Two shared search lists (`ClassSearchList`, `SourceSearchList`) give the card, the
pending-box card and the chip the same search and "Create". Class, recent classes and default
source live in local storage behind small store hooks; a new box or mask reads its class from the
sticky-class store only.

**Tech Stack:** Svelte 5, SvelteKit, TypeScript, svelte/store, shadcn `Command` and `Popover`
(bits-ui), TanStack Query v6, vitest with `@testing-library/svelte`.

**Spec:** `.experimental/superpowers/specs/2026-11-04-annotation-card-design.md`. Decision log:
`.experimental/ux-gap-prototype/annotation-variants/DECISIONS.md`. Mock:
`.experimental/ux-gap-prototype/annotation-variants/box-card-mock/index.html`.

## Global Constraints

- Prototype branch `claude/annotation-workflow-variants-f42327`, not for `main`. Frontend only.
- Settings live in local storage. No backend change, no backend default source.
- Ship value fast, don't break existing flows. Don't polish beyond what the Caltech rerun and
  Igor's review need.
- Out of scope: number keys for classes, smart select and SLIC, video, point clouds,
  classifications, clicking boxes with the box tool, color by class or source (LIG-11395), the
  save reliability holes except `mutateAsync`, removing the Edit button (LIG-10568), the card
  outside edit mode.
- User-facing words follow the glossary: "annotation", "class", "annotation source".
- Exact copy: "Pick a source", "Pick a class" (amber), "Create '<name>'", "Move to…",
  "Type to relabel · Del delete · Esc close", "Collapse all", "Expand all", "Bounding box",
  "Default".
- Frontend guide: components under 100 lines, stores over runes where possible, one folder per
  component or hook, `.svelte.ts` for files using runes or TanStack Query.
- Paths below are relative to `lightly_studio_view/src/lib/` unless they start with
  `lightly_studio_view/` or `.experimental/`.
- Run frontend commands from `lightly_studio_view` after `nvm use` (Node 24.13.1).

## Decisions this plan makes where the spec is silent

Confirm these before execution; each is cheap to flip.

1. **Shortcut letters keep their shortcut.** The spec says typing a letter starts a class search.
   Nine letters are shortcuts already (`v e s d b m a r x`, from `useSettings`). Those keep their
   shortcut, with or without a selection; any other letter or digit starts the search. Clicking
   the class field still lets you type any name. Without this, `v` could never hide annotations
   while the card is open, which the spec requires.
2. **New annotations read the sticky class, not the context label.** Selecting a mask still sets
   the context label to the mask's class (the brush needs it). If a new box read the context
   label, that class would leak into the next box with no explicit pick. So a new box and a new
   mask take their class from `lastAnnotationLabel[collectionId]` only.
3. **Masks keep the centered dialog** for the first stroke with no class (the spec allows this
   fallback). Cancelling it no longer shows a toast.
4. **The card anchors on image coordinates for boxes, masks and the pending box alike:**
   `getBoundingBox(annotation)` mapped through the annotation layer's `getScreenCTM()`. The DOM
   lookup by `data-group-id` goes away, since a mask's group spans the whole image.
5. **Side-panel relabel and `AnnotationDetails` keep setting the sticky class**, as today. The
   spec only removes the call in `useAnnotationSelection.ts`.

## Review Focus

1. A shortcut letter (`v`, `b`, `s`…) pressed with a box selected runs its shortcut and does not
   open the class search. Pinned in Task 1 (`isSearchStartKey`) and Task 5.
2. Typing a class that differs from an existing one only by case (`DEER` for `deer`) picks the
   existing class and offers no "Create". Pinned in Task 1 (`matchClasses`) and Task 4.
3. Esc on the compact card closes it without the panel's Esc handler also switching the tool to
   the select tool. Pinned in Task 5.
4. A default source renamed in Settings stays the default; one that was deleted is ignored and
   the user must pick. Pinned in Task 9.
5. Drawing a second box while the first waits for a class drops the first; it is never saved
   with the second box's class. Pinned in Task 7 (`usePendingBoxClass`).

---

### Task 1: Card helpers

The working tree holds uncommitted Delete-key wiring in `SelectedBoxPanel/` (helper stub, tests,
window listener). This task moves the helpers to the card folder and commits that wiring.

**Files:**
- Move: `components/SampleDetails/SelectedBoxPanel/SelectedBoxPanel.helpers.ts` →
  `components/SampleDetails/AnnotationCard/annotationCard.helpers.ts` (`git mv`)
- Move: `SelectedBoxPanel.helpers.test.ts` → `AnnotationCard/annotationCard.helpers.test.ts`
- Modify: `components/SampleDetails/SelectedBoxPanel/SelectedBoxPanel.svelte` (import the new
  path and name; the file is deleted in Task 5)

**Interfaces:**
- Produces, all in `annotationCard.helpers.ts`:

```ts
export const placePanel: (params: PlacePanelParams) => { left: number; top: number }; // unchanged
export const imageRectToScreen: (
    bbox: BoundingBox,
    matrix: Pick<DOMMatrix, 'a' | 'd' | 'e' | 'f'>
) => Rect;
type KeyPress = Pick<KeyboardEvent, 'key' | 'target' | 'repeat' | 'altKey' | 'ctrlKey' | 'metaKey'>;
export const isDeleteKey: (event: KeyPress) => boolean; // renamed from isDeleteBoxKey
export const isSearchStartKey: (event: KeyPress, shortcutKeys: string[]) => boolean;
export const SHORTCUT_SETTING_KEYS: readonly [
    'key_hide_annotations', 'key_toggle_edit_mode', 'key_toolbar_selection', 'key_toolbar_drag',
    'key_toolbar_bounding_box', 'key_toolbar_segmentation_mask', 'key_toolbar_slic',
    'key_toolbar_brush', 'key_toolbar_eraser'
];
export const getShortcutKeys: (
    settings: Partial<Record<(typeof SHORTCUT_SETTING_KEYS)[number], string | null>>
) => string[];
export const matchClasses: (params: { names: string[]; recent: string[]; query: string }) => {
    matches: string[];
    createName: string | null;
};
export const matchSources: <T extends { name: string }>(params: { sources: T[]; query: string }) => T[];
export const pushRecent: (list: string[], name: string, max?: number) => string[]; // max = 5
export const recentChips: (list: string[], current: string | null, max?: number) => string[]; // max = 3
```

`Rect` is the existing `{ left, top, right, bottom }` interface; export it. `BoundingBox` comes
from `$lib/types`.

- [ ] **Step 1: Move the files and rename `isDeleteBoxKey` to `isDeleteKey`** in the helper, its
  test and `SelectedBoxPanel.svelte`. Keep the `TODO(human)` comment in the body.

- [ ] **Step 2: Write the failing tests** in `annotationCard.helpers.test.ts`, next to the moved
  `placePanel` and `isDeleteKey` tests. One `it` per row group; `press()` is the `isDeleteKey`
  factory with default key `'k'` and `shortcutKeys` `[]`.

| Call | Expected |
|---|---|
| `imageRectToScreen({ x: 5, y: 5, width: 10, height: 20 }, { a: 2, d: 2, e: 10, f: 20 })` | `{ left: 20, top: 30, right: 40, bottom: 70 }` |
| `press()`, `press({ key: 'K' })`, `press({ key: '7' })` | `true` |
| `press({ key: 'v' }, ['v', 'b'])`, `press({ key: 'B' }, ['v', 'b'])` | `false` |
| `press` with `key: 'Enter'`, `key: ' '`, `ctrlKey`, `metaKey`, `repeat`, an `<input>` target, a target inside `role="listbox"` | `false` |
| `getShortcutKeys({ key_hide_annotations: 'V', key_toolbar_bounding_box: 'b', key_toolbar_brush: null })` | `['v', 'b']` |

`matchClasses`, with `names = ['bobcat', 'coyote', 'deer', 'raccoon']` unless the row says:

| `recent` | `query` | `matches` | `createName` |
|---|---|---|---|
| `['deer', 'coyote']` | `''` | `['deer', 'coyote', 'bobcat', 'raccoon']` | `null` |
| `[]` | `'co'` | `['coyote', 'raccoon']` | `'co'` |
| `[]`, names `['bobcat', 'category', 'cat']` | `'cat'` | `['cat', 'category', 'bobcat']` | `null` |
| `['cab']`, names `['cat', 'car', 'cab']` | `'ca'` | `['cab', 'car', 'cat']` | `'ca'` |
| `[]` | `'DEER'` | `['deer']` | `null` |
| `[]` | `'  fox '` | `[]` | `'fox'` |

The order is exact match, then prefix, then substring; recent classes first within a tier, then
alphabetical. An empty query lists recent classes, then the rest alphabetically.

| Call | Expected |
|---|---|
| `matchSources` on names `predictions, labels, model-preds`, query `''` | `labels, model-preds, predictions` |
| same, query `'PRE'` | `predictions, model-preds` |
| `pushRecent(['a', 'b', 'c', 'd', 'e'], 'c')` | `['c', 'a', 'b', 'd', 'e']` |
| `pushRecent(['a', 'b', 'c', 'd', 'e'], 'f')` | `['f', 'a', 'b', 'c', 'd']` |
| `pushRecent(['a'], '  ')` | `['a']` |
| `recentChips(['deer', 'bobcat', 'coyote', 'fox'], 'deer')` | `['bobcat', 'coyote', 'fox']` |
| `recentChips(['deer', 'bobcat', 'coyote', 'fox'], null)` | `['deer', 'bobcat', 'coyote']` |

- [ ] **Step 3: Run them and see the new ones fail**

Run: `npx vitest run src/lib/components/SampleDetails/AnnotationCard/annotationCard.helpers.test.ts`
Expected: FAIL on the new functions (not exported); the `isDeleteKey` tests fail on the stub.

- [ ] **Step 4: Implement the new helpers.** `isSearchStartKey` reuses `isTextInputTarget` and
  `isOverlayTarget` from `$lib/utils` and matches one character with `/^[\p{L}\p{N}]$/u`.
  Matching is case-insensitive on the trimmed query. `isDeleteKey` is the user's `TODO(human)`:
  if its body is still the stub, stop and ask the user to write it before Step 5.

- [ ] **Step 5: Run the helper and panel tests**

Run: `npx vitest run src/lib/components/SampleDetails/AnnotationCard src/lib/components/SampleDetails/SelectedBoxPanel`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add lightly_studio_view/src/lib/components/SampleDetails/AnnotationCard lightly_studio_view/src/lib/components/SampleDetails/SelectedBoxPanel
git commit -m "Delete the selected box with the Delete key and add card helpers"
```

---

### Task 2: Sticky class in local storage

**Files:**
- Create: `hooks/useWebStorage/useWebStorage.ts`, `useWebStorage.test.ts`
- Modify: `hooks/useSessionStorage/useSessionStorage.ts` (delegates to `useWebStorage`)
- Modify: `hooks/useGlobalStorage.ts:72` (`lastAnnotationLabel` uses local storage, same key)
- Create: `hooks/useRecentClasses/useRecentClasses.ts`, `useRecentClasses.test.ts`
- Create: `hooks/useStickyClass/useStickyClass.ts`, `useStickyClass.test.ts`
- Modify: `hooks/useAnnotationSelection/useAnnotationSelection.ts:16,39-43` and its test
- Modify: `hooks/useSegmentationMaskBrush.ts:87-95` and its test
- Modify: `hooks/index.ts` (export the new hooks)

**Interfaces:**
- Produces:

```ts
export function useWebStorage<T extends JsonSerializable>(
    area: 'localStorage' | 'sessionStorage',
    key: string,
    initialValue: T
): Writable<T>;

// key 'lightlyStudio_recent_annotation_classes'
export function useRecentClasses(): {
    recentClasses: Readable<Record<string, string[]>>;
    addRecentClass: (collectionId: string, className: string) => void; // uses pushRecent
};

// Call during component init: it reads the annotation label context.
export function useStickyClass(): {
    /** The class for the next annotation, per collection: the `lastAnnotationLabel` store. */
    stickyClasses: Readable<Record<string, string>>;
    /** An explicit class pick: sets the sticky class, puts it first in the recent list and
     *  sets the context label, so the crosshair color follows. */
    pickClass: (collectionId: string, className: string) => void;
};
```

- Consumes: `pushRecent` (Task 1).

- [ ] **Step 1: Write the failing tests**
  - `useWebStorage.test.ts`: `useWebStorage('localStorage', 'k', {})` set to `{ a: 1 }` writes
    `'{"a":1}'` to `localStorage['k']`; a second `useWebStorage('localStorage', 'k', {})` starts
    as `{ a: 1 }`.
  - `useGlobalStorage.test.ts`: after `updateLastAnnotationLabel('col-1', 'deer')`,
    `JSON.parse(localStorage.getItem('lightlyStudio_last_annotation_label')!)['col-1']` is `'deer'`
    and `sessionStorage` has no such key.
  - `useRecentClasses.test.ts`: `addRecentClass('col-1', 'deer')`, then `'bobcat'` gives
    `{ 'col-1': ['bobcat', 'deer'] }`; adding to `'col-2'` leaves `'col-1'` as is.
  - `useStickyClass.test.ts` (mock `useAnnotationLabelContext`): `pickClass('col-1', 'deer')`
    sets `stickyClasses['col-1']` to `'deer'`, `recentClasses['col-1']` to `['deer']`, and calls
    `setAnnotationLabel('deer')`.
  - `useAnnotationSelection.test.ts`: replace the expectation that selecting calls
    `updateLastAnnotationLabel` with `expect(updateLastAnnotationLabelMock).not.toHaveBeenCalled()`
    for both a box and a mask. Selecting a mask still calls `setAnnotationLabel('<mask class>')`
    and `setStatus('brush')`.
  - `useSegmentationMaskBrush.test.ts`: with no selected annotation, context label `'bobcat'` and
    sticky class `'deer'`, `finishBrush` creates the mask with deer's `annotation_label_id`. With
    no sticky class and `requestLabel` resolving `null`, it calls neither `toast.error` nor
    `createAnnotation`.

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/lib/hooks`
Expected: FAIL in the files above.

- [ ] **Step 3: Implement.** Move the body of `useSessionStorage` into `useWebStorage` (it reads
  `globalThis[area]` and keeps the `typeof … === 'undefined'` guards). In `finishBrush`, a new
  mask takes `get(lastAnnotationLabel)[collectionId]`; after a dialog pick call `pickClass`;
  on cancel return without a toast. Delete the `updateLastAnnotationLabel` call and import from
  `useAnnotationSelection`.

- [ ] **Step 4: Run the hooks tests**

Run: `npx vitest run src/lib/hooks`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/hooks
git commit -m "Keep the class for new annotations per dataset in local storage"
```

---

### Task 3: Settle create and delete after unmount

**Files:**
- Modify: `hooks/useCreateAnnotation/useCreateAnnotation.ts:38-67` and its test
- Modify: `hooks/useDeleteAnnotation/useDeleteAnnotation.ts:31-58` and its test

**Interfaces:**
- Produces: `createAnnotation` and `deleteAnnotation` keep their signatures and return types.

- [ ] **Step 1: Update the tests** to mock `mutateAsync` instead of `mutate`:
  - `createAnnotation` resolves with the response; refetch and `trackEvent('annotation_created', …)`
    run once.
  - `mutateAsync` is called with exactly one argument, the variables
    `{ path: { collection_id: 'col-1' }, body: inputs }`: no per-call callbacks, which TanStack
    drops when the observer unmounts.
  - When `mutateAsync` rejects, `createAnnotation` rejects with the same error and no refetch runs.
  - The same three for `deleteAnnotation`, with `{ path: { collection_id, annotation_id } }`.

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/lib/hooks/useCreateAnnotation src/lib/hooks/useDeleteAnnotation`
Expected: FAIL (`mutateAsync` is not called)

- [ ] **Step 3: Switch both hooks to `await mutation.mutateAsync(variables)`**, then refetch and
  track inside the async function.

- [ ] **Step 4: Run the tests**

Run: same as Step 2. Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/hooks/useCreateAnnotation lightly_studio_view/src/lib/hooks/useDeleteAnnotation
git commit -m "Use mutateAsync so create and delete settle after unmount"
```

---

### Task 4: Shared search lists

**Files:**
- Create: `components/SampleDetails/ClassSearchList/ClassSearchList.svelte`, `ClassSearchList.test.ts`, `index.ts`
- Create: `components/SampleDetails/SourceSearchList/SourceSearchList.svelte`, `SourceSearchList.test.ts`, `index.ts`

**Interfaces:**
- Consumes: `matchClasses`, `matchSources` (Task 1).
- Produces:

```ts
// ClassSearchList props
interface Props {
    names: string[];
    recent: string[];
    initialQuery?: string; // default ''
    onPick: (className: string) => void;
    onCancel: () => void;
}
// SourceSearchList props
interface Props {
    sources: { collection_id: string; name: string }[];
    excludeSourceId?: string;
    onPick: (sourceName: string) => void;
    onCancel: () => void;
}
```

Both render a shadcn `Command` inline (not in a popover) with `shouldFilter={false}` and the
order from the helper. The input is focused on mount. Enter picks the highlighted row, which is
the first row until the arrow keys move it. Esc in the input calls `preventDefault`,
`stopPropagation` and `onCancel`. `ClassSearchList` adds a last row "Create '<name>'" when
`createName` is set. `SourceSearchList` has no create row; with no match it shows
"No annotation source matches" and Enter does nothing.

- [ ] **Step 1: Write the failing tests**
  - `ClassSearchList`: with `names ['bobcat','coyote','deer','raccoon']`, `recent ['deer']`, the
    rows read `deer, bobcat, coyote, raccoon` and the input has focus. Type `co`: rows
    `coyote, raccoon, Create 'co'`; Enter calls `onPick('coyote')`. Type `fox` and Enter:
    `onPick('fox')`. Type `DEER`: no Create row; Enter calls `onPick('deer')`. `initialQuery: 'k'`
    puts `k` in the input. Esc calls `onCancel` once, and a `keydown` listener on `window` does
    not see it.
  - `SourceSearchList`: with sources `labels` (s1), `predictions` (s2), `model-preds` (s3) and
    `excludeSourceId: 's2'`, rows read `labels, model-preds`. Type `lab` and Enter:
    `onPick('labels')`. Type `zzz`: "No annotation source matches", Enter calls nothing. Esc calls
    `onCancel`.

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/lib/components/SampleDetails/ClassSearchList src/lib/components/SampleDetails/SourceSearchList`
Expected: FAIL (components missing)

- [ ] **Step 3: Implement both components.**

- [ ] **Step 4: Run the tests.** Same command. Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/components/SampleDetails/ClassSearchList lightly_studio_view/src/lib/components/SampleDetails/SourceSearchList
git commit -m "Add class and source search lists for the annotation card"
```

---

### Task 5: Annotation card, compact view

**Files:**
- Move: `SelectedBoxPanel/useSelectedBoxActions.svelte.ts` → `AnnotationCard/useAnnotationCardActions.svelte.ts` (`git mv`)
- Create: `components/SampleDetails/AnnotationCard/AnnotationCardFrame.svelte`
- Create: `components/SampleDetails/AnnotationCard/AnnotationCard.svelte`, `AnnotationCard.test.ts`
- Create: `components/SampleDetails/AnnotationCard/AnnotationCardCompact.svelte`
- Modify: `components/SampleDetails/SampleDetailsImageContainer/SampleDetailsImageContainer.svelte:35,200-212,316,428-430`
- Delete: `components/SampleDetails/SelectedBoxPanel/`

**Interfaces:**
- Consumes: `placePanel`, `imageRectToScreen`, `isDeleteKey`, `isSearchStartKey`,
  `getShortcutKeys`, `recentChips` (Task 1); `useStickyClass`, `useRecentClasses` (Task 2).
- Produces:

```ts
export const useAnnotationCardActions: (getParams: () => {
    collectionId: string;
    annotation: AnnotationView;
    refetch: () => void;
}) => {
    labels; sources; isMoving; // as in useSelectedBoxActions
    changeClass: (className: string) => Promise<void>; // undo entry, update, then pickClass
    moveTo: (sourceName: string) => Promise<boolean>;  // never touches the target source
    remove: () => Promise<void>;                       // undo entry, delete, clear selection
    close: () => void;                                 // setAnnotationId(null)
};

// AnnotationCardFrame props: places its children beside `bbox` every animation frame.
interface Props {
    bbox: BoundingBox;                         // image coordinates
    getLayer: () => SVGGraphicsElement | null; // the annotation layer of the canvas
    testId: string;
    children: Snippet;
}

// AnnotationCard props
interface Props {
    collectionId: string;
    annotation: AnnotationView; // a box or a mask
    refetch: () => void;
    getLayer: () => SVGGraphicsElement | null;
}
```

The frame maps `bbox` with `imageRectToScreen(bbox, layer.getScreenCTM())`, takes
`layer.ownerSVGElement.getBoundingClientRect()` as the canvas, and calls `placePanel`. It sets
`visibility: hidden` while `$isHidden` (from `useHideAnnotations`) or
`annotationLabelContext.isDrawing` is true, and stays mounted so typed text survives.

`AnnotationCard` holds `view: 'compact' | 'search' | 'move'` (`compact` only in this task) and
the compact layout from the spec: source button with color dot, confidence to two decimals when
`annotation.confidence` is set, 🗑 (`aria-label="Delete annotation"`), ✕
(`aria-label="Close"`); class field button; recent chips from
`recentChips($recentClasses[collectionId] ?? [], className)`; hint
"Type to relabel · Del delete · Esc close". A `<svelte:window onkeydowncapture>` handler acts
only in `compact` view:

- Esc outside fields and menus: `preventDefault`, `stopPropagation`, `close()`.
- `isDeleteKey`: `preventDefault`, `remove()`.
- `isSearchStartKey(event, getShortcutKeys($settingsStore))`: `preventDefault`, switch to
  `search` with the key as the query (wired in Task 6).

In `SampleDetailsImageContainer`, bind the existing `<g class:invisible={$isHidden}>` as
`annotationLayer`. Replace `selectedBox` with `selectedAnnotation`: edit mode, not the
annotation details view, type `OBJECT_DETECTION` or `SEGMENTATION_MASK`. Drop its `isDrawing`
condition, since the frame hides itself.

- [ ] **Step 1: Write the failing tests** in `AnnotationCard.test.ts`. Mock
  `useAnnotationCardActions` as the old `SelectedBoxPanel.test.ts` did, plus `close`; seed
  `recentClasses` with `{ 'col-1': ['bobcat', 'coyote', 'deer', 'fox'] }`; annotation class
  `bobcat` in source `predictions`. jsdom has no layout, so query hidden elements by label or
  test id.
  - Shows `bobcat`, `predictions` and the chips `coyote, deer, fox`.
  - Clicking chip `coyote` calls `changeClass('coyote')`.
  - `keyDown(document.body, { key: 'Delete' })` and then `'Backspace'` call `remove` twice.
  - Esc on `document.body` calls `close` once, and a `keydown` listener added to `window`
    before the render does not see it.
  - Clicking ✕ calls `close`.
  - Key `v` (the hide shortcut) leaves the card in compact view: no search input appears.

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/lib/components/SampleDetails/AnnotationCard`
Expected: FAIL (`AnnotationCard.svelte` missing)

- [ ] **Step 3: Implement the frame, the compact view and the actions hook**, wire the card into
  `SampleDetailsImageContainer`, and delete `SelectedBoxPanel/`.

- [ ] **Step 4: Run the card and image container tests**

Run: `npx vitest run src/lib/components/SampleDetails`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/components/SampleDetails
git commit -m "Replace the selected box panel with an annotation card"
```

---

### Task 6: Card class search and move list

**Files:**
- Modify: `components/SampleDetails/AnnotationCard/AnnotationCard.svelte`, `AnnotationCard.test.ts`

**Interfaces:**
- Consumes: `ClassSearchList`, `SourceSearchList` (Task 4); `changeClass`, `moveTo` (Task 5).

`search` view: the header stays, the body is `ClassSearchList` with label names, recent classes
and the query. A pick calls `changeClass` and returns to `compact`; cancel returns to `compact`.
Clicking the class field opens `search` with an empty query. `move` view: header text
"Move to…", body `SourceSearchList` without the current source. A pick calls `moveTo` and returns
to `compact` when it resolves `true`; cancel returns to `compact`. The source button opens `move`.

- [ ] **Step 1: Write the failing tests**
  - Key `k` opens the search with `k` in the focused input.
  - Click the class field, type `coy`, press Enter: `changeClass('coyote')`, then the compact
    view shows again.
  - Click the source button: "Move to…" shows and the input has focus. Type `lab` and Enter:
    `moveTo('labels')`.
  - Esc in the move list returns to the compact view, and `close` is not called.

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/lib/components/SampleDetails/AnnotationCard/AnnotationCard.test.ts`
Expected: FAIL on the four new tests.

- [ ] **Step 3: Implement both views.**

- [ ] **Step 4: Run the tests.** Same command. Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/components/SampleDetails/AnnotationCard
git commit -m "Relabel and move from the annotation card"
```

---

### Task 7: First box with no class

**Files:**
- Create: `hooks/usePendingBoxClass/usePendingBoxClass.ts`, `usePendingBoxClass.test.ts`
- Create: `components/SampleDetails/SampleObjectDetectionRect/resolveNewBoxClass.ts`, `resolveNewBoxClass.test.ts`
- Create: `components/SampleDetails/AnnotationCard/PendingBoxCard.svelte`, `PendingBoxCard.test.ts`
- Modify: `components/SampleDetails/SampleObjectDetectionRect/SampleObjectDetectionRect.svelte:64-74,107-110,200-212,355-359,366-369,403-408`
- Modify: `components/SampleDetails/SampleDetailsImageContainer/SampleDetailsImageContainer.svelte` (render `PendingBoxCard`)

**Interfaces:**
- Consumes: `useStickyClass` (Task 2), `ClassSearchList` (Task 4), `AnnotationCardFrame` (Task 5).
- Produces:

```ts
// Module-level store, shared by SampleObjectDetectionRect and the image container.
export function usePendingBoxClass(): {
    request: Readable<{ bbox: BoundingBox } | null>;
    /** Shows the pending-box card at `bbox`. Resolves with the picked class, or null.
     *  A new request resolves the previous one with null. */
    requestClass: (bbox: BoundingBox) => Promise<string | null>;
    resolve: (className: string) => void; // no-op when nothing is pending
    cancel: () => void;                   // no-op when nothing is pending
};

export const resolveNewBoxClass: (params: {
    stickyClass: string | undefined;
    bbox: BoundingBox;
    requestClass: (bbox: BoundingBox) => Promise<string | null>;
}) => Promise<string | null>;

// PendingBoxCard props
interface Props { collectionId: string; getLayer: () => SVGGraphicsElement | null }
```

`PendingBoxCard` shows `AnnotationCardFrame` at the request's bbox with ✕ and a
`ClassSearchList` (recent classes first). A pick calls `pickClass(collectionId, name)` then
`resolve(name)`. Esc, ✕, or a `pointerdown` outside the frame calls `cancel()`.

`SampleObjectDetectionRect` gets the class from
`resolveNewBoxClass({ stickyClass: $stickyClasses[collectionId], bbox, requestClass })`. On
`null` it clears the pending bbox and returns before `createLabel` or `createAnnotation`, with no
toast. It calls `cancel()` on drag start, on destroy and when `sampleId` changes. Remove
`SelectClassDialog`, `useSelectClassDialog`, `updateLastAnnotationLabel` and
`setAnnotationLabel` from it. The image container renders `PendingBoxCard` while `$request` is
set, else `AnnotationCard` for the selection.

- [ ] **Step 1: Write the failing tests**
  - `usePendingBoxClass`: `requestClass(bbox)` then `resolve('deer')` resolves `'deer'` and
    `request` returns to `null`. `cancel()` resolves `null`. A second `requestClass` resolves the
    first with `null` and keeps the second pending. `resolve('x')` with nothing pending throws
    nothing.
  - `resolveNewBoxClass`: sticky `'deer'` gives `'deer'` and never calls `requestClass`; no sticky
    class and `requestClass` resolving `null` gives `null`; resolving `'fox'` gives `'fox'`.
  - `PendingBoxCard` (seed a pending request; mock `pickClass`): the input has focus and recent
    classes come first; type `deer` and Enter calls `pickClass('col-1', 'deer')` and the request
    promise resolves `'deer'`; Esc resolves `null`; `pointerDown(document.body)` resolves
    `null`; ✕ resolves `null`.

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/lib/hooks/usePendingBoxClass src/lib/components/SampleDetails/SampleObjectDetectionRect src/lib/components/SampleDetails/AnnotationCard/PendingBoxCard.test.ts`
Expected: FAIL (modules missing)

- [ ] **Step 3: Implement the store, the helper, the card and the wiring.**

- [ ] **Step 4: Run the tests.** Same command plus `src/lib/components/SampleDetails`. Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/hooks/usePendingBoxClass lightly_studio_view/src/lib/components/SampleDetails
git commit -m "Ask for the class of the first box at the box"
```

---

### Task 8: Target chip

**Files:**
- Create: `hooks/useAnnotationTarget/useSetTargetSource.ts`, `useSetTargetSource.test.ts`
- Modify: `hooks/useAnnotationTarget/useAnnotationTarget.svelte.ts:62-67` (uses `useSetTargetSource`)
- Create: `components/SampleDetails/AnnotationTargetChip/AnnotationTargetChip.svelte`, `AnnotationTargetChip.test.ts`, `index.ts`
- Modify: `components/SampleDetails/SampleDetailsImageContainer/SampleDetailsImageContainer.svelte:269-276` (`toolbarContent`)

**Interfaces:**
- Consumes: `ClassSearchList`, `SourceSearchList` (Task 4); `useStickyClass`, `useRecentClasses`
  (Task 2); `isSearchStartKey`, `getShortcutKeys` (Task 1); `usePendingBoxClass` (Task 7);
  `resolveTargetSource` (existing).
- Produces:

```ts
/** Sets where new annotations go and remembers it for the collection. */
export const useSetTargetSource: (getCollectionId: () => string) => (name: string) => void;

// AnnotationTargetChip props
interface Props { collectionId: string }
```

The chip has two `Popover` triggers. Source part: the dot and
`resolveTargetSource(annotationLabelContext.annotationSource, sourceNames)`, or "Pick a source" in
amber; its popover holds `SourceSearchList`, and a pick calls `setTargetSource`. Class part:
`$stickyClasses[collectionId]`, or "Pick a class" in amber; its popover holds `ClassSearchList`,
and a pick calls `pickClass`. Each closes on pick or cancel. A `<svelte:window onkeydowncapture>`
handler opens the class popover with the key as the query when nothing is selected, no box is
pending and `isSearchStartKey` holds. Render the chip in `toolbarContent` after
`SampleDetailsToolbar`, absolutely placed right of the toolbar column (the toolbar sits at
`absolute left-0 top-0`), and not on the annotation details view.

- [ ] **Step 1: Write the failing tests**
  - `useSetTargetSource`: `'  labels '` sets the context source to `'labels'` and calls
    `updateLastAnnotationSource('col-1', 'labels')`; `'  '` does nothing.
  - `AnnotationTargetChip` (mock collections `labels`, `predictions`; sticky `deer`): shows
    `labels` and `deer`. With no source picked and two sources it shows "Pick a source"; with no
    sticky class it shows "Pick a class". Setting `annotationLabelContext.annotationSource =
    'predictions'` updates the chip, which pins the sync with the radios. Picking `coyote` in the
    class popover calls `pickClass('col-1', 'coyote')`. Picking `predictions` in the source popover
    calls the setter with `'predictions'`. Key `k` with no selection opens the class list with `k`
    in the input; key `k` with a selected annotation and key `b` with none open nothing.

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/lib/hooks/useAnnotationTarget src/lib/components/SampleDetails/AnnotationTargetChip`
Expected: FAIL (modules missing)

- [ ] **Step 3: Implement `useSetTargetSource`, the chip and its placement.**

- [ ] **Step 4: Run the tests.** Same command. Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/hooks/useAnnotationTarget lightly_studio_view/src/lib/components/SampleDetails
git commit -m "Show where new annotations go and their class by the toolbar"
```

---

### Task 9: Default source

**Files:**
- Create: `hooks/useDefaultSource/useDefaultSource.ts`, `useDefaultSource.test.ts`
- Modify: `hooks/useAnnotationTarget/resolveTargetSource.ts` (add `pickInitialSource`) and its test
- Modify: `hooks/useAnnotationTarget/useAnnotationTarget.svelte.ts:44-49` (seed effect)
- Modify: `components/Settings/AnnotationSourcesTab/AnnotationSourceRow/AnnotationSourceRow.svelte`
- Modify: `components/Settings/AnnotationSourcesTab/AnnotationSourceList/AnnotationSourceList.svelte`
- Modify: `components/Settings/AnnotationSourcesTab/AnnotationSourcesTab.svelte`, `AnnotationSourcesTab.test.ts`
- Modify: `components/Settings/AnnotationSourcesTab/useAnnotationSources/useAnnotationSources.svelte.ts:39-49`

**Interfaces:**
- Produces:

```ts
// key 'lightlyStudio_default_annotation_source', in local storage
export function useDefaultSource(): {
    defaultSources: Readable<Record<string, string>>;
    /** At most one default per collection; null removes it. */
    setDefaultSource: (collectionId: string, sourceName: string | null) => void;
    renameDefaultSource: (collectionId: string, oldName: string, newName: string) => void;
};

/** The source to seed when the user has not picked one yet, or null to leave it unpicked. */
export const pickInitialSource: (params: {
    chosenSource: string | null | undefined;
    sourceNames: string[];
    defaultSource: string | undefined;
}) => string | null;
```

`useAnnotationTarget`'s seed effect becomes "if `pickInitialSource(...)` returns a name, call
`setAnnotationSource(name)`". It does not write `lastAnnotationSource`, so the default never
looks like a remembered pick. `AnnotationSourceRow` gets `isDefault: boolean` and
`onToggleDefault: () => void`: a `Switch` with the visible label "Default" and
`aria-label={`Use ${name} as the default annotation source`}`. `AnnotationSourceList` passes
`defaultName: string | null` and `onToggleDefault(source)` through. The tab sets the default to
the row's name when switched on and to `null` when switched off. The rename callback in
`useAnnotationSources` also calls `renameDefaultSource`.

- [ ] **Step 1: Write the failing tests**
  - `useDefaultSource`: setting `labels` on `col-1` stores
    `{ 'col-1': 'labels' }` in local storage; setting `predictions` replaces it; `null` removes the
    entry; `renameDefaultSource('col-1', 'labels', 'gt')` updates it only while `labels` is the
    default.
  - `pickInitialSource`: chosen `labels` gives `null`; one source `['a']` gives `'a'`; default
    `predictions` in `['labels', 'predictions']` gives `'predictions'`; default `gone` not in the
    list gives `null`; no default and two sources gives `null`.
  - `AnnotationSourcesTab.test.ts`: switching "Default" on for `predictions` checks its switch;
    switching it on for `labels` then unchecks `predictions`.

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/lib/hooks/useDefaultSource src/lib/hooks/useAnnotationTarget src/lib/components/Settings/AnnotationSourcesTab`
Expected: FAIL

- [ ] **Step 3: Implement the hook, `pickInitialSource`, the seed effect and the Settings rows.**

- [ ] **Step 4: Run the tests.** Same command. Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/hooks lightly_studio_view/src/lib/components/Settings
git commit -m "Let one annotation source be the default for new annotations"
```

---

### Task 10: Collapse all and "Bounding box"

**Files:**
- Modify: `components/SampleDetails/SampleDetailsAnnotationSegment/SampleDetailsAnnotationSegment.svelte` and its test
- Modify: `components/SampleDetails/SampleDetailsAnnotationSourceGroup/SampleDetailsAnnotationSourceGroup.svelte` and its test
- Modify: `constants.ts:6`
- Modify: `components/SampleDetails/SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte:70-73` and its test

**Interfaces:**
- Produces: `SampleDetailsAnnotationSourceGroup` gets `collapsed?: boolean` (default `false`).
  While `true` the rows are not rendered and the chevron shows closed. The group's own `open`
  state is untouched, so "Expand all" brings back each group as it was.

The segment holds `rowsCollapsed` and renders a `headerAction` button "Collapse all" or
"Expand all". It passes `collapsed={rowsCollapsed}` to every group and, in the ungrouped layout,
skips the rows. Headers, radios, the hint and the new-source input stay.

- [ ] **Step 1: Write the failing tests**
  - Segment with two sources: clicking "Collapse all" removes every
    `sample-details-pannel-annotation-name` and keeps every `annotation-source-group-header`; in
    edit mode the `annotation-target-radio-<name>` radios stay. The button now reads
    "Expand all"; clicking it brings the rows back.
  - Segment with one source: "Collapse all" hides the rows.
  - `SampleDetailsSidePanelAnnotation` shows "Bounding box" for an `object_detection` annotation.

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/lib/components/SampleDetails/SampleDetailsAnnotationSegment src/lib/components/SampleDetails/SampleDetailsAnnotationSourceGroup src/lib/components/SampleDetails/SampleDetailsSidePanel`
Expected: FAIL

- [ ] **Step 3: Implement**, and set `ANNOTATION_TYPES.object_detection` to `'Bounding box'`.

- [ ] **Step 4: Run the tests.** Same command. Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src/lib/constants.ts lightly_studio_view/src/lib/components/SampleDetails
git commit -m "Add Collapse all to the Annotations panel and say Bounding box"
```

---

### Task 11: Remove drag and drop and the pencil variant

**Files:**
- Delete: `components/SampleDetails/AnnotationSourceDropZone/`
- Delete: `components/SampleDetails/SampleDetailsAnnotationSegment/annotationSourceDrop.ts`, `annotationSourceDrop.test.ts`
- Modify: `SampleDetailsAnnotationSegment.svelte` (drop `draggedAnnotation`, `canDropOn`, `dropDraggedAnnotationOn`, the drop zone wrapper and the drag props)
- Modify: `SampleDetailsSidePanelAnnotation.svelte:11-12,35-36,54-67,146-159` (grip, `onDragStart`, `onDragEnd`)
- Delete: `hooks/useAnnotateVariant/`, `components/SampleDetails/AnnotationTargetButton/`
- Delete: `components/SampleDetails/AnnotationTargetControl/` (callers use `AnnotationTargetRadio`, wrapped in `{#if $isEditingMode}`)
- Modify: `AnnotationTargetHint.svelte`, `AnnotationTargetCaption.svelte`, `SampleDetailsClassificationSegment.svelte` (drop the variant check)
- Modify: `hooks/useAnnotationTarget/resolveTargetSource.ts` (rename `PENCIL_PICK_MESSAGE` to `PICK_SOURCE_MESSAGE` with the radio text), `useAnnotationTarget.svelte.ts` (no variant lookup), `hooks/index.ts`
- Modify: the tests that reference any of these

**Interfaces:**
- Produces: `PICK_SOURCE_MESSAGE = 'Choose where new annotations go: pick a source in the Annotations panel.'`,
  the default `pickMessage` of `getTargetBlockedReason`.

- [ ] **Step 1: Update the tests first.** Delete the drag, drop-zone and variant tests. Add to
  `SampleDetailsSidePanelAnnotation.test.ts`: in edit mode,
  `queryByTestId('annotation-drag-handle')` is `null`. Add to
  `SampleDetailsAnnotationSegment.test.ts`: in edit mode with two sources and no URL param, the
  `annotation-target-radio-<name>` radios render.

- [ ] **Step 2: Remove the code.**

- [ ] **Step 3: Check nothing still refers to it**

Run: `grep -rnE "annotateVariant|AnnotateVariant|AnnotationSourceDropZone|ANNOTATION_DRAG_TYPE|PENCIL_PICK_MESSAGE|AnnotationTargetButton|AnnotationTargetControl|SelectedBoxPanel|useSelectedBoxActions" src`
Expected: no output

- [ ] **Step 4: Run the affected tests**

Run: `npx vitest run src/lib/components/SampleDetails src/lib/hooks`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lightly_studio_view/src
git commit -m "Remove drag and drop between sources and the pencil variant"
```

---

### Task 12: Checks and GUI walkthrough

- [ ] **Step 1: Static checks.** Run `make static-checks` in `lightly_studio_view`. Expected: no
  lint or type errors. If `npm run check` reports missing `./generated/...` modules, run the
  generate steps first (`npm run generate-api-client && npm run generate-language`).
- [ ] **Step 2: Unit tests.** Run `npx vitest run`. Expected: PASS.
- [ ] **Step 3: GUI walkthrough on the Caltech demo DB** (servers and DBs in
  `/Users/gabrielfruet/Library/Application Support/Claude/side-session-notes/local_32fab9ee-b48a-444f-9d6a-17a8d2a9fe91/annotation-variants.md`).
  Clear the `lightlyStudio_*` keys in local storage first. Take one screenshot for each:
  1. Draw the first box with no class: the card opens at the box, Esc drops it and no request
     reaches the server. Draw again and pick `deer`. The next box saves as `deer` with no card
     prompt. Go to the next image: no card, and the chip keeps its source and class.
  2. Relabel a box by typing a class, then with a recent chip.
  3. Move a prediction to `labels` from the card. The chip still shows the old target.
  4. Delete with the Delete key, then undo with Cmd+Z after the card has closed.
  5. Select a mask and relabel it from the card. Deselect, draw a box: it gets the chip's class.
  6. Hold `v`: the card and the annotations hide.
  7. Collapse all, then Expand all.
  8. Mark `labels` as Default in Settings, open a new tab on the dataset, enter edit mode: the
     chip shows `labels`.
- [ ] **Step 4: Write the results** (pass or fail per item, screenshot paths) to
  `.experimental/ux-gap-prototype/annotation-variants/CARD_GUI_CHECK.md` and commit it.
