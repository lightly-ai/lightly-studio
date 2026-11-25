import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { addCuboidSelectionListeners, pickSmallestFromIntersections } from './cuboidSelection';

describe('pickSmallestFromIntersections', () => {
    it('returns null when there are no intersections', () => {
        expect(pickSmallestFromIntersections([])).toBeNull();
    });

    it('returns the annotation ID of the only intersected cuboid', () => {
        expect(pickSmallestFromIntersections([{ annotationId: 'cuboid-1', volume: 8 }])).toBe(
            'cuboid-1'
        );
    });

    it('returns the smallest-volume cuboid when multiple cuboids are hit', () => {
        expect(
            pickSmallestFromIntersections([
                { annotationId: 'outer', volume: 100 },
                { annotationId: 'inner', volume: 4 }
            ])
        ).toBe('inner');
    });

    it('returns the smallest-volume cuboid regardless of intersection order', () => {
        expect(
            pickSmallestFromIntersections([
                { annotationId: 'inner', volume: 4 },
                { annotationId: 'outer', volume: 100 }
            ])
        ).toBe('inner');
    });
});

describe('addCuboidSelectionListeners', () => {
    const canvas = document.createElement('canvas');
    const onselect = vi.fn();
    let cuboidClicked = false;
    let cleanup = () => {};
    const defaultParams: Parameters<typeof addCuboidSelectionListeners>[0] = {
        canvas,
        activeTool: 'select',
        onselect,
        isCuboidClicked: () => cuboidClicked,
        resetCuboidClicked: () => (cuboidClicked = false)
    };
    beforeEach(() => {
        vi.clearAllMocks();
        cuboidClicked = false;
    });
    afterEach(() => cleanup());

    it('deselects on Escape and empty canvas clicks with the select tool', async () => {
        cleanup = addCuboidSelectionListeners(defaultParams);

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
        expect(onselect).toHaveBeenCalledWith(null);
        onselect.mockClear();
        canvas.click();
        await Promise.resolve();
        expect(onselect).toHaveBeenCalledExactlyOnceWith(null);
    });

    it('preserves selection on a gizmo click, then allows an empty canvas click to clear it', async () => {
        cleanup = addCuboidSelectionListeners(defaultParams);
        cuboidClicked = true;

        canvas.click();
        await Promise.resolve();
        expect(onselect).not.toHaveBeenCalled();
        canvas.click();
        await Promise.resolve();
        expect(onselect).toHaveBeenCalledExactlyOnceWith(null);
    });

    it('keeps the selection when Escape is pressed in a text field or a popover', () => {
        cleanup = addCuboidSelectionListeners({ ...defaultParams, activeTool: 'select' });
        const input = document.createElement('input');
        const popover = document.createElement('div');
        popover.setAttribute('role', 'dialog');
        const button = document.createElement('button');
        popover.append(button);
        document.body.append(input, popover);

        input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
        button.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));

        expect(onselect).not.toHaveBeenCalled();
        input.remove();
        popover.remove();
    });

    it('leaves selection unchanged while creating cuboids', async () => {
        cleanup = addCuboidSelectionListeners({ ...defaultParams, activeTool: 'create-cuboid' });
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
        canvas.click();
        await Promise.resolve();
        expect(onselect).not.toHaveBeenCalled();
    });

    it('removes the listeners when the layer is disposed', async () => {
        cleanup = addCuboidSelectionListeners(defaultParams);
        cleanup();
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
        canvas.click();
        await Promise.resolve();
        expect(onselect).not.toHaveBeenCalled();
    });
});
