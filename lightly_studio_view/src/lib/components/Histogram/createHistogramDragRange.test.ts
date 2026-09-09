import { describe, expect, it, vi } from 'vitest';
import { createHistogramDragRange } from './createHistogramDragRange.svelte';
import type { HistogramRange } from './types';

// Bin i spans [i, i + 1): five bins over [0, 5].
const BIN_EDGES = [0, 1, 2, 3, 4, 5];

const setup = (onRangeSelect?: (range: HistogramRange) => void) =>
    createHistogramDragRange({
        getBinEdges: () => BIN_EDGES,
        getOnRangeSelect: () => onRangeSelect
    });

describe('createHistogramDragRange', () => {
    it('has no range before a drag starts', () => {
        expect(setup(vi.fn()).range).toBeUndefined();
    });

    it('spans from the pressed bin to the bin under the pointer', () => {
        const drag = setup(vi.fn());
        drag.start(1);
        drag.move(3);
        expect(drag.range).toEqual({ min: 1, max: 4 });
    });

    it('spans the same interval when dragged right to left', () => {
        const drag = setup(vi.fn());
        drag.start(3);
        drag.move(1);
        expect(drag.range).toEqual({ min: 1, max: 4 });
    });

    it('selects just the pressed bin when the pointer never moves', () => {
        const onRangeSelect = vi.fn();
        const drag = setup(onRangeSelect);
        drag.start(2);
        drag.end();
        expect(onRangeSelect).toHaveBeenCalledWith({ min: 2, max: 3 });
    });

    it('clears the preview once the drag is committed', () => {
        const drag = setup(vi.fn());
        drag.start(0);
        drag.move(2);
        drag.end();
        expect(drag.range).toBeUndefined();
    });

    it('ignores a drag when there is no handler to select into', () => {
        const drag = setup(undefined);
        drag.start(1);
        drag.move(3);
        expect(drag.range).toBeUndefined();
    });

    it('ignores pointer movement that did not start with a press', () => {
        const drag = setup(vi.fn());
        drag.move(3);
        expect(drag.range).toBeUndefined();
    });

    it('calls the handler the component holds now, not the one it had at setup', () => {
        // `onRangeSelect` is a prop: capturing it once would pin the mount value.
        const first = vi.fn();
        const second = vi.fn();
        let current = first;
        const drag = createHistogramDragRange({
            getBinEdges: () => BIN_EDGES,
            getOnRangeSelect: () => current
        });

        current = second;
        drag.start(1);
        drag.end();

        expect(first).not.toHaveBeenCalled();
        expect(second).toHaveBeenCalledWith({ min: 1, max: 2 });
    });
});
