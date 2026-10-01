import { describe, expect, it } from 'vitest';
import { AnnotationCountMode, AnnotationType } from '$lib/api/lightly_studio_local/types.gen';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { buildImageAnnotationCountsBySampleTagsQueryKey } from './buildImageAnnotationCountsBySampleTagsQueryKey';
import { buildImageAnnotationCountsBySampleTagsRequest } from './buildImageAnnotationCountsBySampleTagsRequest';

const params = {
    collectionId: 'collection-1',
    sampleTagIds: ['tag-b', 'tag-a'],
    filter: { width: { min: 200, max: 800 } },
    annotationType: AnnotationType.OBJECT_DETECTION,
    countMode: AnnotationCountMode.SAMPLES
};

describe('buildImageAnnotationCountsBySampleTagsQueryKey', () => {
    it('keeps the annotation-count prefix and every request input in the query key', () => {
        expect(buildImageAnnotationCountsBySampleTagsQueryKey(params)).toEqual([
            ...useImageAnnotationCountsQueryKey,
            'by-sample-tags',
            buildImageAnnotationCountsBySampleTagsRequest(params)
        ]);
    });

    it('produces different keys for different tag orderings', () => {
        expect(buildImageAnnotationCountsBySampleTagsQueryKey(params)).not.toEqual(
            buildImageAnnotationCountsBySampleTagsQueryKey({
                ...params,
                sampleTagIds: [...params.sampleTagIds].reverse()
            })
        );
    });
});
