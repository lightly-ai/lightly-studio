import { QueryClient, useQueryClient, type QueryKey } from '@tanstack/svelte-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    countVideoFrameAnnotationsByVideoCollectionQueryKey,
    countVideoFrameAnnotationsQueryKey,
    readAnnotationCollectionsQueryKey,
    readAnnotationCollectionsWithCountsQueryKey,
    readCollectionHierarchyQueryKey,
    readImageQueryKey,
    readTagsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getAnnotationsInfiniteQueryKeyPrefix } from '$lib/hooks/useAnnotationsInfinite/createAnnotationsInfiniteOptions';
import { getImagesInfiniteQueryKeyPrefix } from '$lib/hooks/useImagesInfinite/createImagesInfiniteOptions';
import { useInvalidateAnnotationSourceQueries } from './useInvalidateAnnotationSourceQueries';

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    useQueryClient: vi.fn()
}));

const path = (collection_id: string) => ({ path: { collection_id } });

describe('useInvalidateAnnotationSourceQueries', () => {
    let client: QueryClient;
    const seed = (queryKey: QueryKey) => client.setQueryData(queryKey, {});
    const isInvalidated = (queryKey: QueryKey) => client.getQueryState(queryKey)?.isInvalidated;

    beforeEach(() => {
        client = new QueryClient();
        vi.mocked(useQueryClient).mockReturnValue(client);
    });

    it('refreshes the sources, the grids and the sample details', () => {
        const affected = [
            readAnnotationCollectionsQueryKey(path('owner')),
            readAnnotationCollectionsWithCountsQueryKey(path('owner')),
            [...getImagesInfiniteQueryKeyPrefix('owner'), 'normal'],
            [...getAnnotationsInfiniteQueryKeyPrefix('source-1'), {}],
            readImageQueryKey({ path: { sample_id: 'sample-1' } }),
            readCollectionHierarchyQueryKey(path('owner')),
            countVideoFrameAnnotationsQueryKey({
                path: { video_frame_collection_id: 'frames-1' },
                body: {}
            }),
            countVideoFrameAnnotationsByVideoCollectionQueryKey({
                ...path('videos-1'),
                body: {}
            })
        ];
        affected.forEach(seed);

        useInvalidateAnnotationSourceQueries()('owner');

        for (const queryKey of affected) expect(isInvalidated(queryKey)).toBe(true);
    });

    it('leaves queries that do not show annotation sources alone', () => {
        const unaffected = [
            readTagsQueryKey(path('owner')),
            [...getImagesInfiniteQueryKeyPrefix('other-dataset'), 'normal']
        ];
        unaffected.forEach(seed);

        useInvalidateAnnotationSourceQueries()('owner');

        for (const queryKey of unaffected) expect(isInvalidated(queryKey)).toBe(false);
    });
});
