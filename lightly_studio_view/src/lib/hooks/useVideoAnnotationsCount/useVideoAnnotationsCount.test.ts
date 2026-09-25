import { describe, expect, it } from 'vitest';
import { AnnotationType } from '$lib/api/lightly_studio_local/types.gen';
import { buildVideoAnnotationCountsRequest } from './useVideoAnnotationsCount';

describe('buildVideoAnnotationCountsRequest', () => {
    it('sends the filter and the annotation type', () => {
        const filter = { filter_type: 'video' as const, width: { min: 100 } };

        expect(
            buildVideoAnnotationCountsRequest({
                collectionId: 'col-1',
                filter,
                annotationType: AnnotationType.CLASSIFICATION
            })
        ).toEqual({
            path: { collection_id: 'col-1' },
            body: { filter, annotation_type: AnnotationType.CLASSIFICATION }
        });
    });

    it('omits the annotation type when it is not given', () => {
        expect(
            buildVideoAnnotationCountsRequest({ collectionId: 'col-1' }).body
        ).not.toHaveProperty('annotation_type');
    });
});
