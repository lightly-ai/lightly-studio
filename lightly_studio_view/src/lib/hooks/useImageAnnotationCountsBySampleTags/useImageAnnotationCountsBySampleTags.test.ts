import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryOptions, CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { countImageAnnotationsBySampleTags } from '$lib/api/lightly_studio_local/sdk.gen';
import { AnnotationCountMode, AnnotationType } from '$lib/api/lightly_studio_local/types.gen';
import { buildImageAnnotationCountsBySampleTagsRequest } from './buildImageAnnotationCountsBySampleTagsRequest';
import { useImageAnnotationCountsBySampleTags } from './useImageAnnotationCountsBySampleTags.svelte';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    countImageAnnotationsBySampleTags: vi.fn()
}));

const params = {
    collectionId: 'collection-1',
    sampleTagIds: ['tag-b', 'tag-a'],
    filter: { width: { min: 200, max: 800 } },
    annotationType: AnnotationType.OBJECT_DETECTION,
    countMode: AnnotationCountMode.SAMPLES
};

describe('useImageAnnotationCountsBySampleTags', () => {
    const queryResult = { data: undefined, subscribe: vi.fn() } as unknown as CreateQueryResult<
        unknown,
        Error
    >;

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(queryResult);
    });

    it('disables the query when the comparison selection is empty', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');
        useImageAnnotationCountsBySampleTags(() => ({ ...params, sampleTagIds: [] }));

        const options = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        expect(options.enabled).toBe(false);
    });

    it('respects an explicit disabled state with selected tags', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');
        useImageAnnotationCountsBySampleTags(() => ({ ...params, enabled: false }));

        const options = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        expect(options.enabled).toBe(false);
    });

    it('forwards the request and cancellation signal to the SDK', async () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');
        const signal = new AbortController().signal;
        vi.mocked(countImageAnnotationsBySampleTags).mockResolvedValue({
            data: []
        } as unknown as Awaited<ReturnType<typeof countImageAnnotationsBySampleTags>>);
        useImageAnnotationCountsBySampleTags(() => params);

        const options = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        await (options.queryFn as (context: { signal: AbortSignal }) => Promise<unknown>)({
            signal
        });

        expect(countImageAnnotationsBySampleTags).toHaveBeenCalledWith({
            ...buildImageAnnotationCountsBySampleTagsRequest(params),
            signal,
            throwOnError: true
        });
    });
});
