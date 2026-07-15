import { describe, it, expect } from 'vitest';
import { buildImageAnnotationCountsRequest } from './useImageAnnotationCounts';
import { AnnotationCountMode, AnnotationType } from '$lib/api/lightly_studio_local/types.gen';

describe('buildImageAnnotationCountsRequest', () => {
    it('includes count_mode in the request body when countMode is provided', () => {
        const request = buildImageAnnotationCountsRequest({
            collectionId: 'col-1',
            annotationType: AnnotationType.OBJECT_DETECTION,
            countMode: AnnotationCountMode.SAMPLES
        });

        expect(request.body).toEqual(
            expect.objectContaining({ count_mode: AnnotationCountMode.SAMPLES })
        );
    });

    it('omits count_mode from the request body when countMode is not provided', () => {
        const request = buildImageAnnotationCountsRequest({
            collectionId: 'col-1',
            annotationType: AnnotationType.OBJECT_DETECTION
        });

        expect(request.body).toEqual(
            expect.objectContaining({ annotation_type: AnnotationType.OBJECT_DETECTION })
        );
        expect(request.body).not.toHaveProperty('count_mode');
    });
});
