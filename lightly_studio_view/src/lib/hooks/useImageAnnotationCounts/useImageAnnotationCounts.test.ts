import { describe, it, expect } from 'vitest';
import {
    buildImageAnnotationCountsQueryKey,
    buildImageAnnotationCountsRequest,
    useImageAnnotationCountsQueryKey
} from './useImageAnnotationCounts';
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

describe('buildImageAnnotationCountsQueryKey', () => {
    const params = {
        collectionId: 'col-1',
        filter: { sample_filter: { tag_ids: ['tag-a'] } },
        annotationType: AnnotationType.OBJECT_DETECTION,
        countMode: AnnotationCountMode.SAMPLES
    };

    it('keeps the annotation-count prefix and every request input in the query key', () => {
        expect(buildImageAnnotationCountsQueryKey(params)).toEqual([
            ...useImageAnnotationCountsQueryKey,
            buildImageAnnotationCountsRequest(params)
        ]);
    });

    it('starts with queryKeyOverride when one is given', () => {
        const queryKeyOverride = [...useImageAnnotationCountsQueryKey, 'distribution'];

        expect(buildImageAnnotationCountsQueryKey({ ...params, queryKeyOverride })).toEqual([
            ...queryKeyOverride,
            buildImageAnnotationCountsRequest(params)
        ]);
    });

    it('produces different keys for different tag filters', () => {
        expect(buildImageAnnotationCountsQueryKey(params)).not.toEqual(
            buildImageAnnotationCountsQueryKey({
                ...params,
                filter: { sample_filter: { tag_ids: ['tag-b'] } }
            })
        );
    });

    it('produces different keys for different collections', () => {
        expect(buildImageAnnotationCountsQueryKey(params)).not.toEqual(
            buildImageAnnotationCountsQueryKey({ ...params, collectionId: 'col-2' })
        );
    });
});
