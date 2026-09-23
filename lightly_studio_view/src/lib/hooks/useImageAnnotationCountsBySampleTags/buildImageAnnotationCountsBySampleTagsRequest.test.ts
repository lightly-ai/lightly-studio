import { describe, expect, it } from 'vitest';
import { AnnotationCountMode, AnnotationType } from '$lib/api/lightly_studio_local/types.gen';
import { buildImageAnnotationCountsBySampleTagsRequest } from './buildImageAnnotationCountsBySampleTagsRequest';

const params = {
    collectionId: 'collection-1',
    sampleTagIds: ['tag-b', 'tag-a'],
    filter: { width: { min: 200, max: 800 } },
    annotationType: AnnotationType.OBJECT_DETECTION,
    countMode: AnnotationCountMode.SAMPLES
};

describe('buildImageAnnotationCountsBySampleTagsRequest', () => {
    it('builds the complete request while preserving ordered tag IDs', () => {
        expect(buildImageAnnotationCountsBySampleTagsRequest(params)).toEqual({
            path: { collection_id: 'collection-1' },
            body: {
                sample_tag_ids: ['tag-b', 'tag-a'],
                filter: { width: { min: 200, max: 800 } },
                annotation_type: AnnotationType.OBJECT_DETECTION,
                count_mode: AnnotationCountMode.SAMPLES
            }
        });
    });

    it('omits optional fields when not provided', () => {
        const result = buildImageAnnotationCountsBySampleTagsRequest({
            collectionId: 'collection-1',
            sampleTagIds: ['tag-a']
        });
        expect(result.body).toEqual({ sample_tag_ids: ['tag-a'] });
    });
});
