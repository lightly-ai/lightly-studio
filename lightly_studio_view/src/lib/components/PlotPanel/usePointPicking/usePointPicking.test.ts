import { describe, expect, it, vi } from 'vitest';
import { usePointPicking } from './usePointPicking';

const CLICKED_POINT = [{ x: 0, y: 0, identifier: 'sample-1' }];

// jsdom has no PointerEvent, so a MouseEvent stands in for it.
const pointerDown = (init: MouseEventInit) =>
    new MouseEvent('pointerdown', init) as unknown as PointerEvent;

const setup = (pickedSampleIds: string[] = []) => {
    const commitPickedSampleIds = vi.fn();
    const picking = usePointPicking({
        getPickedSampleIds: () => pickedSampleIds,
        getHoveredSampleId: () => 'hovered-sample',
        commitPickedSampleIds
    });
    return { ...picking, commitPickedSampleIds };
};

describe('usePointPicking', () => {
    it('adds the clicked sample on shift-click and removes a picked one', () => {
        const added = setup(['sample-0']);
        added.onPointerDown(pointerDown({ shiftKey: true }));
        added.onSelection(CLICKED_POINT);
        expect(added.commitPickedSampleIds).toHaveBeenCalledWith(['sample-0', 'sample-1']);

        const removed = setup(['sample-1']);
        removed.onPointerDown(pointerDown({ shiftKey: true }));
        removed.onSelection(CLICKED_POINT);
        expect(removed.commitPickedSampleIds).toHaveBeenCalledWith([]);
    });

    it('ignores a click without shift', () => {
        const { onPointerDown, onSelection, commitPickedSampleIds } = setup();
        onPointerDown(pointerDown({ shiftKey: false }));
        onSelection(CLICKED_POINT);
        expect(commitPickedSampleIds).not.toHaveBeenCalled();
    });

    it('treats a shift-drag shorter than 6px as a click on the hovered sample', () => {
        const { onPointerDown, isShortShiftDrag, pickPressedPoint, commitPickedSampleIds } =
            setup();
        onPointerDown(pointerDown({ shiftKey: true, clientX: 10, clientY: 10 }));

        expect(isShortShiftDrag(new MouseEvent('mouseup', { clientX: 14, clientY: 10 }))).toBe(
            true
        );
        expect(isShortShiftDrag(new MouseEvent('mouseup', { clientX: 20, clientY: 10 }))).toBe(
            false
        );
        pickPressedPoint();
        expect(commitPickedSampleIds).toHaveBeenCalledWith(['hovered-sample']);
    });

    it('does not treat a drag without shift as a click', () => {
        const { onPointerDown, isShortShiftDrag } = setup();
        onPointerDown(pointerDown({ shiftKey: false, clientX: 10, clientY: 10 }));
        expect(isShortShiftDrag(new MouseEvent('mouseup', { clientX: 11, clientY: 10 }))).toBe(
            false
        );
    });
});
