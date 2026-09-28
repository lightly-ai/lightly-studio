import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as tanstackQuery from '@tanstack/svelte-query';
import * as svelteQueryGen from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { AnnotationType } from '$lib/api/lightly_studio_local/types.gen';
import {
    buildVideoAnnotationCountsRequest,
    useVideoAnnotationCounts
} from './useVideoAnnotationsCount';

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

describe('useVideoAnnotationCounts', () => {
    const baseOptions = { queryKey: ['video-annotation-counts'], queryFn: vi.fn() };
    let queryOptionsThunk: () => {
        enabled: boolean;
        placeholderData: (previousData: unknown) => unknown;
    };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(
            svelteQueryGen,
            'countVideoFrameAnnotationsByVideoCollectionOptions'
        ).mockReturnValue(
            baseOptions as unknown as ReturnType<
                typeof svelteQueryGen.countVideoFrameAnnotationsByVideoCollectionOptions
            >
        );
        vi.spyOn(tanstackQuery, 'createQuery').mockImplementation((thunk) => {
            queryOptionsThunk = thunk as typeof queryOptionsThunk;
            return {} as ReturnType<typeof tanstackQuery.createQuery>;
        });
    });

    it('builds the request and is enabled by default', () => {
        useVideoAnnotationCounts(() => ({ collectionId: 'col-1' }));

        expect(queryOptionsThunk()).toEqual({
            ...baseOptions,
            placeholderData: expect.any(Function),
            enabled: true
        });
        expect(
            svelteQueryGen.countVideoFrameAnnotationsByVideoCollectionOptions
        ).toHaveBeenCalledWith(buildVideoAnnotationCountsRequest({ collectionId: 'col-1' }));
    });

    it('passes enabled through without sending it in the request', () => {
        useVideoAnnotationCounts(() => ({ collectionId: 'col-1', enabled: false }));

        expect(queryOptionsThunk().enabled).toBe(false);
        expect(
            svelteQueryGen.countVideoFrameAnnotationsByVideoCollectionOptions
        ).toHaveBeenCalledWith(buildVideoAnnotationCountsRequest({ collectionId: 'col-1' }));
    });

    it('keeps the previous counts while the next request runs', () => {
        useVideoAnnotationCounts(() => ({ collectionId: 'col-1' }));
        const previousData = [{ label_name: 'car', total_count: 3 }];

        expect(queryOptionsThunk().placeholderData(previousData)).toBe(previousData);
    });
});
