# Color Picker Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-written plumbing of `ui/color-picker` with the bits-ui Popover, `d3-color`, and the bits-ui Slider. Split the picker into small components. Users see no change.

**Architecture:** `color-picker.svelte` keeps the public API and renders a bits-ui Popover. The open state and the preview and revert logic are in the rune module `color-picker-state.svelte.ts`. The panel content is in small components: the saturation box, the hue slider and the preset swatches. The color state has one source of truth (`hsl` and `hex`, set together by two setters). There are no `$effect`s that sync the two.

**Tech Stack:** Svelte 5, bits-ui 1.8.0 (Popover, Slider), d3-color 3, vitest with @testing-library/svelte.

**Spec:** There is no separate design document. The design was approved in chat on 2026-11-03:
- Keep our own panel: same look, 16 presets, hex field, opacity, and Cancel/Apply.
- Keep the live preview. Cancel, Escape and a click outside restore the original color.
- Do not change the call sites: `AnnotationColorLegend.svelte` and `SideMenu/ColorMarker/ColorMarker.svelte`.
- Popover replaces the portal, the positioning and the dismissal code.
- `d3-color` replaces the hex↔HSL math.
- The hue bar uses a Slider.
- The saturation box stays custom, with pointer events and pointer capture.
- Fix the wrong `role="dialog"` on the inner areas, and label the hex input.
- Split the code into components under 100 lines.
- Add a test for the picker inside a modal dialog.
- The library `svelte-awesome-color-picker` was evaluated and rejected: it needs too many CSS overrides.

## Global Constraints

- Node 24.13.1. Run `nvm use` in `lightly_studio_view` before `npm`, `npx` or `make`.
- Do not change the public API in `ui/color-picker/index.ts`: the export is `ColorPicker`, and the props are `initialColor`, `initialAlpha`, `onChange(color, alpha)`, `onClose(applied)`, `position`, `class` and `children`.
- The user-visible text stays the same: "Color", "Opacity", "Presets", "Cancel", "Apply", and the 16 preset hex values.
- Files in `ui/color-picker/` use kebab-case, like the other shadcn folders. Test wrappers follow the repo pattern `<Name>TestWrapper.test.svelte`.
- Each `.svelte` file must be under 100 lines and each function under 20 lines (frontend-guide, best-practices).
- `d3-color` is `^3.1.0` in `dependencies`, and `@types/d3-color` is `^3.1.3` in `devDependencies`. Both are already in the lockfile.
- Load the skills `frontend-guide` and `best-practices` before you edit a file.
- Before each commit, run `make static-checks` and `npx vitest run src/lib/components/ui/color-picker`. Both must pass.
- End commit messages with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Picker inside the Settings modal dialog** (Settings → Annotation classes). Clicking or typing in the panel must not close the dialog. Escape closes only the picker. Focus can reach the hex input. Owner: Task 1 test. The Annotation classes tab is not yet shown in Settings, so no dialog in the app uses the picker, and only the test covers this case.
2. **Preview, then dismiss, then reopen.** The original color is restored. After Apply, reopening starts from the new `initialColor`. Owner: Task 1 test.
3. **Trigger inside a clickable row** (side menu). A click on the trigger must not reach the parent's click handler. Owner: Task 1 test.
4. **Presets that do not round-trip through rounded HSL.** For example, `#888888` would become `#878787`. Selecting a preset must preview exactly that hex. Owner: Task 2 test.
5. **Typing in the hex field.** A partial value (`#12`) changes nothing. An uppercase value (`#00FF00`) is accepted and previewed as lowercase `#00ff00`. Owner: Task 4 test.

## PR Stack

| PR | Branch (based on) | Tasks |
|---|---|---|
| #3020 | `michal-lig-11481-refactor-color-picker-popover` (`main`) | Task 1 |
| #3021 | `michal-lig-11481-refactor-color-picker-color-state` (#3020) | Task 2 |
| #3022 | `michal-lig-11481-refactor-color-picker-saturation-box` (#3021) | Task 3 |
| #3023 | `michal-lig-11481-refactor-color-picker-panel` (#3022) | Task 4, plus the fixes from the final review |

Each task runs in a fresh subagent. The first version of the plan put Tasks 2 and 3 in one PR. We split it so that each PR has one purpose.

## Changes During Execution

All tasks are done. These points differ from the first version of the plan:

- **`role="dialog"`:** bits-ui 1.8.0 does not add `role="dialog"` to the Popover content. `color-picker.svelte` sets it explicitly. The keyboard handlers at the window level (`isOverlayTarget`) also rely on it.
- **`align`:** the Popover content defaults to `align="center"`. The old panel was top-aligned for `left` and `right`. `color-picker.svelte` sets `align="start"` for those sides. Task 1 missed this; the final review found it, and the fix is in #3023.
- **`Hsl` type:** it is not exported, because the frontend guide says not to export types. Consumers use `ReturnType<typeof hexToHsl>`.
- **State module:** the state, the setters, `schedulePreview()`, `applyChanges()` and `cancelChanges()` moved from `color-picker.svelte` to `color-picker-state.svelte.ts`, so that `color-picker.svelte` is under 100 lines. The factory `createColorPickerState` is about 115 lines of flat helpers, each under 20 lines.
- **Tests:** jsdom has no `PointerEvent`, so the tests add a stand-in in `beforeAll`. The bits-ui dismiss check needs events with coordinates.
- **Focus and animation:** bits-ui focuses the ✕ button when the panel opens, and the panel fades in instead of sliding in. Both were accepted.
- **Manual checks:** done in Chrome against a COCO dataset, in the side menu and in sample details. Panel and marker positions match `main`.

---

## PR 1 (#3020)

### Task 1: Use the bits-ui Popover for opening, placement and dismissal

**Files:**
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.svelte`
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.test.ts`
- Create: `lightly_studio_view/src/lib/components/ui/color-picker/ColorPickerInDialogTestWrapper.test.svelte`

**Interfaces:**
- Consumes: `Popover`, `PopoverTrigger` and `PopoverContent` from `$lib/components/ui/popover` (bits-ui 1.8.0). `Dialog` from `$lib/components/ui/dialog` (only in the test wrapper).
- Produces: `color-picker.svelte` with the same public props. The Popover content keeps `aria-label="Color picker"` (bits-ui gives it `role="dialog"`). Later tasks rely on the functions `applyChanges()` and `cancelChanges()`, and on `schedulePreview()` (requestAnimationFrame throttle), staying in this file.

- [x] **Step 1: Update the tests to describe the new behavior**

In `color-picker.test.ts`:
- Delete the tests `opens inside a transformed modal dialog and positions relative to it` and `positions relative to the viewport outside a modal dialog`. Floating UI now owns the placement.
- In `restores the original color when dismissing a preview`, replace `fireEvent.mouseDown(document.body)` with the events that the bits-ui dismissible layer reacts to: `fireEvent.pointerDown(document.body)`, then `fireEvent.pointerUp(document.body)`, then `fireEvent.click(document.body)`. Keep the assertions.
- Add these tests:

```ts
it('restores the original color when pressing Escape after a preview', async () => {
    // open, click preset '#0000ff', wait for onChange('#0000ff', 1)
    await fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' });
    expect(onChange).toHaveBeenLastCalledWith('#ff0000', 1);
    expect(screen.queryByRole('dialog', { name: 'Color picker' })).not.toBeInTheDocument();
});

it('starts from the new initial color after apply and reopen', async () => {
    // render with initialColor '#ff0000'; open; click preset '#0000ff'; click 'Apply'
    expect(onClose).toHaveBeenLastCalledWith(true);
    // rerender with { initialColor: '#0000ff' }; open again
    expect(screen.getByRole('textbox')).toHaveValue('#0000ff');
    // click 'Cancel' without previewing: onChange call count stays the same
});

it('does not propagate the trigger click to a parent element', async () => {
    const parentClick = vi.fn();
    // render with a target div that has a click listener parentClick
    await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));
    expect(parentClick).not.toHaveBeenCalled();
    expect(screen.getByRole('dialog', { name: 'Color picker' })).toBeInTheDocument();
});

it('works inside a modal dialog without closing it', async () => {
    render(ColorPickerInDialogTestWrapper, { props: { onChange } });
    await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));
    await fireEvent.click(screen.getByTitle('#0000ff'));
    await waitFor(() => expect(onChange).toHaveBeenLastCalledWith('#0000ff', 1));
    await fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' });
    expect(screen.queryByRole('dialog', { name: 'Color picker' })).not.toBeInTheDocument();
    expect(screen.getByRole('dialog', { name: 'Host dialog' })).toBeInTheDocument();
});
```

`ColorPickerInDialogTestWrapper.test.svelte` renders `<Dialog.Root open>` with `<Dialog.Content aria-label="Host dialog">`. Inside it is `<ColorPicker {onChange}>` with a `<span>Open color picker</span>` child.

- [x] **Step 2: Run the tests and check that the new ones fail**

Run: `npx vitest run src/lib/components/ui/color-picker`
Expected: the Escape, propagation and modal dialog tests FAIL. The old drag and preview tests PASS.

- [x] **Step 3: Rewrite the open and close code in `color-picker.svelte` with the Popover**

- Use `<Popover.Root bind:open={isOpen} onOpenChange={handleOpenChange}>`. `handleOpenChange(open: boolean): void` resets the state from `initialColor` and `initialAlpha` when the popover opens. It calls `cancelChanges()` when the user dismisses it (Escape or a click outside). `applyChanges()` and `cancelChanges()` set `isOpen = false` themselves. bits-ui does not call `onOpenChange` for changes the code makes, so there is no double revert.
- `<Popover.Trigger>` replaces the `<button>`. Keep the classes `m-0 border-0 bg-transparent p-0`. Its `onclick` calls `e.stopPropagation()` only. Do not call `preventDefault`, because the trigger must still toggle.
- `<Popover.Content side={position} sideOffset={8} collisionPadding={10} aria-label="Color picker">` uses the classes `w-56 p-0` plus `className`. Keep `onclick` and `onmousedown` → `stopPropagation()` on the content. Canvas listeners at the document level must not see clicks in the panel. Remove `preventDefault` there, because the hex input needs focus.
- Delete these: `getPortalTarget`, `togglePicker`, `handleKeyDown`, `setupClickOutside`, `updatePickerPosition`, `getTransformedAncestor`, the `$effect` that registers them, the `id="color-picker-panel"`, the `fly` transition and the `DialogPrimitive` import. Delete the TODO comment as well.
- The header's ✕ button and the Cancel button call `cancelChanges()`. The Apply button calls `applyChanges()`. Do not change these.

- [x] **Step 4: Run the tests and check that they pass**

Run: `npx vitest run src/lib/components/ui/color-picker`
Expected: all tests PASS.

- [x] **Step 5: Check manually in the app**

Use the `run` skill to start the app with any dataset. Check these in a browser:
- **Settings → Annotation classes:** open a class color. Drag in the saturation box, type in the hex field, press Escape. Only the picker closes and the color is restored.
- **Side menu, label color marker:** the picker opens to the right of the marker and flips near the edge of the screen. A click outside restores the color, and Apply keeps it.

If the host dialog closes or the hex input cannot get focus, stop and report back. Do not add workarounds.

- [x] **Step 6: Run the static checks and commit**

Run: `make static-checks`. Expected: no errors.

```bash
git add src/lib/components/ui/color-picker
git commit -m "Use Popover for the color picker panel"
```

---

## PR 2 (#3021 and #3022)

### Task 2: One color state, with `d3-color` doing the conversions

**Files:**
- Modify: `lightly_studio_view/package.json` and `package-lock.json` (with `npm install d3-color@^3.1.0 && npm install -D @types/d3-color@^3.1.3`)
- Create: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.helpers.ts`
- Create: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.helpers.test.ts`
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.svelte`
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.test.ts`

**Interfaces:**
- Produces, in `color-picker.helpers.ts`:
  - `interface Hsl { h: number; s: number; l: number }`, where `h` is 0–360 and `s` and `l` are 0–100, all integers.
  - `hexToHsl(hex: string): Hsl`, using `hsl()` from d3-color. Map the `NaN` that d3 gives for gray colors to `0`, and round each value.
  - `hslToHex(value: Hsl): string`, using d3-color `hsl(h, s / 100, l / 100).formatHex()`. The result is lowercase.
  - `isHexColor(value: string): boolean` checks for `#` plus exactly 6 hex digits, in any case.
- Produces, in `color-picker.svelte`: the state `hsl: Hsl` and `hex: string` and two setters, `setFromHex(hex: string): void` and `setFromHsl(value: Hsl): void`. Each setter sets both fields and calls `schedulePreview()`. Delete both `$effect`s and the local `hexToHsl` and `hslToHex`.

- [x] **Step 1: Write the helper tests**

```ts
it.each([
    ['#ff0000', { h: 0, s: 100, l: 50 }],
    ['#ff8080', { h: 0, s: 100, l: 75 }],
    ['#888888', { h: 0, s: 0, l: 53 }],
    ['#000000', { h: 0, s: 0, l: 0 }]
])('hexToHsl(%s)', (hex, expected) => expect(hexToHsl(hex)).toEqual(expected));

it('hslToHex returns lowercase hex', () => expect(hslToHex({ h: 120, s: 100, l: 50 })).toBe('#00ff00'));

it.each([['#00FF00', true], ['#12', false], ['00ff00', false], ['#00ff0g', false]])(
    'isHexColor(%s) is %s', (value, expected) => expect(isHexColor(value)).toBe(expected));
```

Add a test to `color-picker.test.ts`: `'previews a gray preset exactly'`. Open the picker, click `getByTitle('#888888')`, and expect `onChange` to be last called with `('#888888', 1)`.

- [x] **Step 2: Run the tests and check that they fail**

Run: `npx vitest run src/lib/components/ui/color-picker`
Expected: the helper tests FAIL because the module is missing. The gray preset test FAILS with `#878787`.

- [x] **Step 3: Install the dependencies and write the helpers. Change the component to use `setFromHex` and `setFromHsl`**

- The preset click and the valid hex input call `setFromHex`.
- Dragging in the saturation box and the hue bar call `setFromHsl`.
- When the picker opens, set the state with `hex = initialColor` and `hsl = hexToHsl(initialColor)`. Do not preview at that point.

- [x] **Step 4: Run the tests and check that they pass**

Run: `npx vitest run src/lib/components/ui/color-picker`. Expected: all tests PASS.

- [x] **Step 5: Run the static checks and commit**

```bash
git add package.json package-lock.json src/lib/components/ui/color-picker
git commit -m "Use d3-color for color picker conversions"
```

### Task 3: Saturation box with pointer events and keyboard support

**Files:**
- Create: `lightly_studio_view/src/lib/components/ui/color-picker/saturation-box.svelte`
- Create: `lightly_studio_view/src/lib/components/ui/color-picker/saturation-box.test.ts`
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.svelte`
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.test.ts`

**Interfaces:**
- Consumes: `Hsl` from `./color-picker.helpers`.
- Produces: `saturation-box.svelte` with the props `{ hsl: Hsl; onPick: (saturation: number, lightness: number) => void }`. The root element has `role="slider"`, `aria-label="Saturation and lightness"`, `aria-valuetext="Saturation {s}%, lightness {l}%"` and `tabindex="0"`.

- [x] **Step 1: Write the component tests**

Mock `getBoundingClientRect` to return `{ left: 0, top: 0, width: 100, height: 100 }`. jsdom has no `setPointerCapture`, so stub it with `HTMLElement.prototype.setPointerCapture = vi.fn()` in `beforeAll`.

```ts
it('picks on pointer down and follows the drag until pointer up', async () => {
    await fireEvent.pointerDown(box, { clientX: 100, clientY: 25, pointerId: 1 });
    expect(onPick).toHaveBeenLastCalledWith(100, 75);
    await fireEvent.pointerMove(box, { clientX: 50, clientY: 50, pointerId: 1 });
    expect(onPick).toHaveBeenLastCalledWith(50, 50);
    await fireEvent.pointerUp(box, { pointerId: 1 });
    await fireEvent.pointerMove(box, { clientX: 0, clientY: 0, pointerId: 1 });
    expect(onPick).toHaveBeenCalledTimes(2);
});

it('clamps positions outside the box', ...); // pointerDown at (150, -20) → onPick(100, 100)

it('moves with the arrow keys', ...); // hsl {h:0,s:50,l:50}: ArrowRight → (51, 50); ArrowDown → (50, 49); Shift+ArrowUp → (50, 60)
```

In `color-picker.test.ts`:
- Delete the `it.each` test `registers one mousemove listener for a drag on %s`.
- Change `previews the selected color while dragging`. Query `getByRole('slider', { name: 'Saturation and lightness' })` and use `pointerDown` (plus the `setPointerCapture` stub). Keep the expectation `('#ff8080', 1)`.

- [x] **Step 2: Run the tests and check that they fail**

Run: `npx vitest run src/lib/components/ui/color-picker`. Expected: the new tests FAIL.

- [x] **Step 3: Write `saturation-box.svelte` and use it in `color-picker.svelte`**

- A pointer down picks a color, calls `setPointerCapture` and sets `isDragging`.
- A pointer move picks a color only while `isDragging`.
- A pointer up or a pointer cancel clears `isDragging`.
- Map the position the same way as today: `x` gives saturation 0–100, and the top of the box is lightness 100.
- The arrow keys move by 1, or by 10 with Shift. Left and Right change saturation, Up and Down change lightness. Clamp to 0–100 and call `preventDefault`.
- Keep the current gradient background and the indicator markup.
- In `color-picker.svelte`, replace the old box, `updateSaturationAndLightness` and `handleSaturationPick` with `<SaturationBox {hsl} onPick={(s, l) => setFromHsl({ ...hsl, s, l })} />`.

- [x] **Step 4: Run the tests and check that they pass**

Run: `npx vitest run src/lib/components/ui/color-picker`. Expected: all tests PASS.

- [x] **Step 5: Run the static checks and commit**

```bash
git add src/lib/components/ui/color-picker
git commit -m "Use pointer events in the color picker saturation box"
```

---

## PR 3 (#3023)

### Task 4: Hue slider, preset swatches, and splitting the panel

**Files:**
- Create: `lightly_studio_view/src/lib/components/ui/color-picker/hue-slider.svelte`
- Create: `lightly_studio_view/src/lib/components/ui/color-picker/preset-swatches.svelte`
- Create: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker-panel.svelte`
- Create: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker-panel.test.ts`
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.svelte`
- Modify: `lightly_studio_view/src/lib/components/ui/color-picker/color-picker.test.ts`

**Interfaces:**
- Consumes: `Hsl`, `isHexColor` from `./color-picker.helpers`. `SaturationBox` from Task 3. `Slider as SliderPrimitive` from `bits-ui`. `Slider` from `$lib/components/ui/slider` (for opacity, as today).
- Produces:
  - `hue-slider.svelte`: props `{ hue: number; onHueChange: (hue: number) => void }`. Use `SliderPrimitive.Root type="single" min={0} max={360} step={1}`. The track has the current rainbow gradient and no Range fill. The thumb has `aria-label="Hue"`. The shadcn `Slider` is not used here because it hardcodes its track and range styles.
  - `preset-swatches.svelte`: props `{ selectedColor: string; onSelect: (color: string) => void }`. It owns the `PRESET_COLORS` constant. Each button has `title={color}`, `aria-label={color}` and `aria-pressed={color === selectedColor}`.
  - `color-picker-panel.svelte`: props `{ hsl: Hsl; hex: string; alpha: number; onHslChange: (value: Hsl) => void; onHexChange: (hex: string) => void; onAlphaChange: (alpha: number) => void; onApply: () => void; onCancel: () => void }`. It renders the header, `SaturationBox`, `HueSlider`, the hex row, opacity, `PresetSwatches` and the actions. The hex input has `aria-label="Hex color"`. It calls `onHexChange(value.toLowerCase())` only when `isHexColor(value)` is true.
  - `color-picker.svelte`: keeps only the Popover, the state, the setters, and the preview, apply and cancel logic. It renders `<ColorPickerPanel>`.

- [x] **Step 1: Write the tests**

`color-picker-panel.test.ts` uses `defaultProps` with `vi.fn()` callbacks:

```ts
it('changes the hue with the keyboard', ...);        // hsl.h = 10; focus slider 'Hue'; ArrowRight → onHslChange({ ...hsl, h: 11 })
it('accepts uppercase hex and ignores partial hex', ...); // type '#12' → onHexChange not called; type '#00FF00' → onHexChange('#00ff00')
it('marks the selected preset', ...);                // hex '#0000ff' → getByRole('button', { name: '#0000ff' }) has aria-pressed="true"
```

In `color-picker.test.ts`, the existing preview, cancel, dismiss, Escape and modal dialog tests must pass without changes.

- [x] **Step 2: Run the tests and check that they fail**

Run: `npx vitest run src/lib/components/ui/color-picker`. Expected: the panel tests FAIL because the module is missing.

- [x] **Step 3: Write the three components and reduce `color-picker.svelte` to the Popover plus the state**

- Remove `role="dialog"` from every element inside the panel.
- Each `.svelte` file must be under 100 lines. Check with `wc -l src/lib/components/ui/color-picker/*.svelte`.

- [x] **Step 4: Run the tests and check that they pass**

Run: `npx vitest run src/lib/components/ui/color-picker`. Expected: all tests PASS.

- [x] **Step 5: Run all the checks and commit**

- Run `make static-checks` and `make test`. Expected: both pass.
- Repeat the manual check from Task 1, Step 5. Also check that the hue bar responds to dragging and to the arrow keys.

```bash
git add src/lib/components/ui/color-picker
git commit -m "Split the color picker panel and use a Slider for hue"
```
