import { describe, expect, it } from 'vitest';
import { AnnotationType } from '$lib/api/lightly_studio_local';
import { previewToCreateInput } from './useSaveAnnotationPreviews.helpers';

const preview = {
    bbox: { x: 1, y: 1, width: 2, height: 2 },
    segmentation_mask: [10, 1, 1],
    score: null
};

describe('previewToCreateInput', () => {
    it('converts a preview to a mask or box create input', () => {
        expect(previewToCreateInput({ preview, saveAs: 'box' })).toEqual({
            annotation_type: AnnotationType.OBJECT_DETECTION,
            x: 1,
            y: 1,
            width: 2,
            height: 2
        });
        expect(previewToCreateInput({ preview, saveAs: 'mask' })).toEqual({
            annotation_type: AnnotationType.SEGMENTATION_MASK,
            x: 1,
            y: 1,
            width: 2,
            height: 2,
            segmentation_mask: preview.segmentation_mask
        });
    });
});
