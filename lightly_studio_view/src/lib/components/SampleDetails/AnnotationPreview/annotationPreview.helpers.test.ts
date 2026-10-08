import { describe, expect, it } from 'vitest';
import { AnnotationType } from '$lib/api/lightly_studio_local';
import { decodeRLEToBinaryMask } from '$lib/components/SampleAnnotation/utils';
import {
    boxFromPoints,
    getAnnotationPreviewErrorMessage,
    isDragBox,
    normalizedPointFromEvent,
    previewToCreateInput,
    previewToFullImageRLE,
    resolveAnnotationClassName
} from './annotationPreview.helpers';

// A 2x2 bbox at (1, 1) with only the bottom-right pixel set: RLE [3, 1].
const preview = {
    bbox: { x: 1, y: 1, width: 2, height: 2 },
    segmentation_mask: [3, 1],
    score: null,
    class_name: null
};
const image = { width: 4, height: 3 };

describe('annotationPreview.helpers', () => {
    it('normalizes and clamps pointer positions to the image', () => {
        const rect = { left: 10, top: 20, width: 100, height: 50 };
        expect(normalizedPointFromEvent({ clientX: 60, clientY: 45 }, rect)).toEqual({
            x: 0.5,
            y: 0.5
        });
        expect(normalizedPointFromEvent({ clientX: 0, clientY: 100 }, rect)).toEqual({
            x: 0,
            y: 1
        });
    });

    it('builds a box from any two corners and ignores tiny drags', () => {
        const box = boxFromPoints({ x: 0.6, y: 0.2 }, { x: 0.1, y: 0.5 });
        expect(box.x).toBeCloseTo(0.1);
        expect(box.y).toBeCloseTo(0.2);
        expect(box.width).toBeCloseTo(0.5);
        expect(box.height).toBeCloseTo(0.3);
        expect(isDragBox(box)).toBe(true);
        expect(isDragBox(boxFromPoints({ x: 0.5, y: 0.5 }, { x: 0.501, y: 0.6 }))).toBe(false);
    });

    it('pastes the cropped preview mask into a full-image mask', () => {
        const mask = decodeRLEToBinaryMask(previewToFullImageRLE(preview, image), 4, 3);
        expect(Array.from(mask)).toEqual([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]);
    });

    it('converts a preview to a mask or box create input', () => {
        expect(previewToCreateInput({ preview, outputType: 'box', image })).toEqual({
            annotation_type: AnnotationType.OBJECT_DETECTION,
            x: 1,
            y: 1,
            width: 2,
            height: 2
        });
        const mask = previewToCreateInput({ preview, outputType: 'mask', image });
        expect(mask.annotation_type).toBe(AnnotationType.SEGMENTATION_MASK);
        expect(mask.segmentation_mask).toEqual([10, 1, 1]);
    });

    it('picks the first non-blank annotation class name', () => {
        expect(resolveAnnotationClassName([null, '  ', ' car ', 'dog'])).toBe('car');
        expect(resolveAnnotationClassName([undefined, ''])).toBe('object');
    });

    it('reads the error message from the response body', () => {
        expect(getAnnotationPreviewErrorMessage({ error: 'Provider unavailable' })).toBe(
            'Provider unavailable'
        );
        expect(getAnnotationPreviewErrorMessage({ detail: 'Bad request' })).toBe('Bad request');
        expect(getAnnotationPreviewErrorMessage(new Error('boom'))).toBe('boom');
        expect(getAnnotationPreviewErrorMessage(undefined)).toBe('Unknown error');
    });
});
