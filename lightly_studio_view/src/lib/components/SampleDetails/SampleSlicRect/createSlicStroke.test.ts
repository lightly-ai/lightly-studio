import { describe, expect, it, vi } from 'vitest';
import { createSlicMaskEditor } from './createSlicMaskEditor';
import { createSlicStroke } from './createSlicStroke';

function setup() {
    const editor = createSlicMaskEditor({
        width: 2,
        height: 1,
        segmentation: {
            width: 2,
            height: 1,
            labels: new Int32Array([0, 1]),
            boundaries: new Uint8Array([1, 1]),
            segmentCount: 2,
            labelPixelIndexes: [[0], [1]],
            pixelIndexes: new Uint32Array([0, 1]),
            segmentOffsets: new Uint32Array([0, 1, 2])
        }
    });
    const onActiveChange = vi.fn();
    const stroke = createSlicStroke({ getEditor: () => editor, onActiveChange });
    return { editor, stroke, onActiveChange };
}

describe('createSlicStroke', () => {
    it('selects regions while dragging and commits once', () => {
        const { stroke, onActiveChange } = setup();
        expect(stroke.begin({ x: 0, y: 0 })?.mask).toEqual(new Uint8Array([1, 0]));
        expect(stroke.extend({ x: 1, y: 0 })?.mask).toEqual(new Uint8Array([1, 1]));
        expect(stroke.commit()).toEqual(new Uint8Array([1, 1]));
        expect(stroke.commit()).toBeNull();
        expect(onActiveChange.mock.calls).toEqual([[true], [false]]);
    });

    it('cancels without changing the mask and allows a fresh stroke', () => {
        const { editor, stroke } = setup();
        stroke.begin({ x: 0, y: 0 });
        stroke.cancel();
        expect(editor.getMask()).toEqual(new Uint8Array([0, 0]));
        expect(stroke.commit()).toBeNull();
        stroke.begin({ x: 1, y: 0 });
        expect(stroke.commit()).toEqual(new Uint8Array([0, 1]));
    });

    it('ignores blocked starts, missing editors, and starts during a stroke', () => {
        const { stroke, onActiveChange } = setup();
        expect(stroke.begin({ x: 0, y: 0 }, true)).toBeNull();
        expect(onActiveChange).not.toHaveBeenCalled();
        stroke.begin({ x: 0, y: 0 });
        expect(stroke.begin({ x: 1, y: 0 })).toBeNull();
        expect(stroke.commit()).toEqual(new Uint8Array([1, 0]));
        const unavailable = createSlicStroke({ getEditor: () => null, onActiveChange });
        expect(unavailable.begin({ x: 0, y: 0 })).toBeNull();
        expect(unavailable.extend({ x: 0, y: 0 })).toBeNull();
    });
});
