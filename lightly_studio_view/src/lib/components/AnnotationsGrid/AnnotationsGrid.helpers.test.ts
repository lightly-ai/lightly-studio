import { describe, expect, it } from 'vitest';
import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
import { buildClassificationDragData } from './AnnotationsGrid.helpers';

const annotation = {
    sample_id: 'ann-1',
    annotation_collection_id: 'col-1',
    annotation_label: { annotation_label_name: 'cat' },
    annotation_type: AnnotationType.CLASSIFICATION
} as unknown as AnnotationView;

const cropWindow = {
    sourceUrl: 'blob:source',
    sampleWidth: 800,
    sampleHeight: 600,
    windowWidth: 100,
    windowHeight: 100,
    windowX: 0,
    windowY: 0
};

describe('buildClassificationDragData', () => {
    it('returns undefined when cropWindow is undefined', () => {
        const result = buildClassificationDragData({
            annotation,
            cropWindow: undefined,
            cropUrl: undefined
        });

        expect(result).toBeUndefined();
    });

    it('uses cropUrl when provided', () => {
        const result = buildClassificationDragData({
            annotation,
            cropWindow,
            cropUrl: 'blob:crop'
        });

        expect(result?.url).toBe('blob:crop');
        expect(result?.fileName).toBe('cat-crop.png');
        expect(result).not.toHaveProperty('annotationSampleId');
        expect(result).not.toHaveProperty('annotationCollectionId');
    });

    it('falls back to sourceUrl when cropUrl is undefined', () => {
        const result = buildClassificationDragData({
            annotation,
            cropWindow,
            cropUrl: undefined
        });

        expect(result?.url).toBe('blob:source');
        expect(result?.fileName).toBe('cat-crop.png');
        expect(result).not.toHaveProperty('annotationSampleId');
        expect(result).not.toHaveProperty('annotationCollectionId');
    });
});
