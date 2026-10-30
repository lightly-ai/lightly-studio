import { describe, expect, it } from 'vitest';
import { createSuperpixelMaskEditor, toSegmentation } from '@lightly-ai/slic';
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
    it.each([false, true])('covers cell corners in reverse: %s', (reverse) => {
        const editor = createSlicMaskEditor({
            segmentation: toSegmentation(new Int32Array([0, 1, 0, 0, 0, 0, 0, 0, 0]), 3, 3),
            width: 3,
            height: 3
        });
        const points = [
            { x: 0.1, y: 0.1 },
            { x: 2.1, y: 2.08 }
        ];
        if (reverse) points.reverse();
        editor.beginStroke(points[0]);
        editor.extendStroke(points[1]);
        expect(editor.commitStroke()).toEqual(new Uint8Array(9).fill(1));
    });

    it.each([
        [133, 1080],
        [140, 1440]
    ])('maps %s columns to %s without spill or skipped pixels', (source, width) => {
        const labels = Int32Array.from({ length: source * 2 }, (_, i) => i);
        const editor = createSlicMaskEditor({
            segmentation: toSegmentation(labels, source, 2),
            width,
            height: 2
        });
        for (let x = 0; x < width; x++) {
            const preview = editor.beginStroke({ x, y: 0 });
            expect(preview.mask[x]).toBe(1);
            expect(preview.mask.subarray(width).some(Boolean)).toBe(false);
        }
    });

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
        expect(editor.beginStroke({ x: 3, y: 1 }).mask).toEqual(
            new Uint8Array([1, 0, 1, 1, 0, 0, 1, 1])
        );
        expect(editor.commitStroke()).toEqual(new Uint8Array([1, 0, 1, 1, 0, 0, 1, 1]));
    });

    it('previews erasing existing pixels and restores them when cancelled', () => {
        const editor = createSlicMaskEditor({
            segmentation,
            width: 4,
            height: 1,
            segmentationMask: [0, 1, 1, 1, 1]
        });
        const selection = editor.beginStroke({ x: 0, y: 0 });
        expect(selection.mode).toBe('erase');
        expect(selection.mask).toEqual(new Uint8Array([0, 0, 1, 0]));
        editor.cancelStroke();
        expect(editor.getMask()).toEqual(new Uint8Array([1, 0, 1, 0]));
        expect(editor.commitStroke()).toBeNull();
        expect(editor.extendStroke({ x: 3, y: 0 })).toBeNull();
    });

    it('skips unchanged previews and interpolates through cells between pointer events', () => {
        const editor = createSlicMaskEditor({ segmentation, width: 4, height: 1 });
        editor.beginStroke({ x: 0, y: 0 });
        expect(editor.extendStroke({ x: 1, y: 0 })).toBeNull();
        expect(editor.extendStroke({ x: 3, y: 0 })?.mask).toEqual(new Uint8Array([1, 1, 1, 1]));
        expect(editor.extendStroke({ x: 0, y: 0 })).toBeNull();
        expect(editor.commitStroke()).toEqual(new Uint8Array([1, 1, 1, 1]));
    });

    it('matches the library mask for noninteger scaling and add/erase strokes', () => {
        const options = { segmentation, width: 5, height: 3, segmentationMask: [0, 1, 14] };
        const editor = createSlicMaskEditor(options);
        const reference = createSuperpixelMaskEditor({
            segmentation,
            mask: editor.getMask(),
            targetWidth: options.width,
            targetHeight: options.height
        });
        for (const point of [
            { x: 4, y: 2 },
            { x: 0, y: 0 }
        ]) {
            editor.beginStroke(point);
            reference.beginStroke(point);
            editor.extendStroke({ x: 2, y: 1 });
            reference.extendStroke({ x: 2, y: 1 });
            expect(editor.commitStroke()).toEqual(reference.commitStroke());
        }
    });
});
