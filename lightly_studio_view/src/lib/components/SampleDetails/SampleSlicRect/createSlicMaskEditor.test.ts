import { describe, expect, it } from 'vitest';
import { createSlicMaskEditor } from './createSlicMaskEditor';

const segmentation = {
    width: 2,
    height: 1,
    labels: new Int32Array([0, 1]),
    boundaries: new Uint8Array([1, 1]),
    segmentCount: 2,
    labelPixelIndexes: [[0], [1]],
    pixelIndexes: new Uint32Array([0, 1]),
    segmentOffsets: new Uint32Array([0, 1, 2])
};

describe('createSlicMaskEditor', () => {
    it('starts with an empty mask and adds a superpixel', () => {
        const editor = createSlicMaskEditor({ segmentation, width: 2, height: 1 });
        expect(editor.getMask()).toEqual(new Uint8Array([0, 0]));
        editor.beginStroke({ x: 1, y: 0 });
        expect(editor.commitStroke()).toEqual(new Uint8Array([0, 1]));
    });

    it('preserves an existing mask and scales superpixels to the original image', () => {
        const editor = createSlicMaskEditor({
            segmentation,
            width: 4,
            height: 2,
            segmentationMask: [0, 1, 7]
        });
        expect(editor.getMask()).toEqual(new Uint8Array([1, 0, 0, 0, 0, 0, 0, 0]));
        editor.beginStroke({ x: 3, y: 1 });
        expect(editor.commitStroke()).toEqual(new Uint8Array([1, 0, 1, 1, 0, 0, 1, 1]));
    });
});
