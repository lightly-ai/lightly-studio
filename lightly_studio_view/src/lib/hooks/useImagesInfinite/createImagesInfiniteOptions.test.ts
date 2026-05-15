import { describe, expect, it, vi, beforeEach } from 'vitest';
import { createImagesInfiniteOptions } from './createImagesInfiniteOptions';
import type { SortFieldExpr } from '$lib/api/lightly_studio_local';

type Options = ReturnType<typeof createImagesInfiniteOptions>;
type QueryFnContext = { pageParam: number; signal: AbortSignal };

const callQueryFn = (options: Options, ctx: QueryFnContext) => {
    const fn = options.queryFn as (ctx: QueryFnContext) => Promise<unknown>;
    return fn(ctx);
};

const { readImagesMock } = vi.hoisted(() => ({ readImagesMock: vi.fn() }));

vi.mock('$lib/api/lightly_studio_local', () => ({
    readImages: (...args: unknown[]) => readImagesMock(...args)
}));

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [])
}));

describe('createImagesInfiniteOptions', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        readImagesMock.mockResolvedValue({ data: { data: [], total_count: 0, nextCursor: null } });
    });

    describe('query key', () => {
        it('includes collection_id and mode', () => {
            const options = createImagesInfiniteOptions({ collection_id: 'col-1', mode: 'normal' });
            expect(options.queryKey[1]).toBe('col-1');
            expect(options.queryKey[2]).toBe('normal');
        });

        it('puts filters in query key for normal mode', () => {
            const filters = { tag_ids: ['t1'] };
            const options = createImagesInfiniteOptions({
                collection_id: 'col-1',
                mode: 'normal',
                filters
            });
            expect(options.queryKey[3]).toBe(filters);
        });

        it('puts classifierSamples in query key for classifier mode', () => {
            const classifierSamples = { positiveSampleIds: ['s1'], negativeSampleIds: [] };
            const options = createImagesInfiniteOptions({
                collection_id: 'col-1',
                mode: 'classifier',
                classifierSamples
            });
            expect(options.queryKey[3]).toBe(classifierSamples);
        });

        it('includes sort_by in query key', () => {
            const sort: SortFieldExpr[] = [
                { source: 'image', field_name: 'score', direction: 'desc', is_numeric: false }
            ];
            const options = createImagesInfiniteOptions({
                collection_id: 'col-1',
                mode: 'normal',
                sort_by: sort
            });
            expect(options.queryKey).toContain(sort);
        });

        it('includes null in query key when sort_by is null', () => {
            const options = createImagesInfiniteOptions({
                collection_id: 'col-1',
                mode: 'normal',
                sort_by: null
            });
            expect(options.queryKey).toContain(null);
        });

        it('produces different keys for different sort_by values', () => {
            const sort1: SortFieldExpr[] = [
                { source: 'image', field_name: 'score', direction: 'desc', is_numeric: false }
            ];
            const sort2: SortFieldExpr[] = [
                { source: 'image', field_name: 'filename', direction: 'asc', is_numeric: false }
            ];
            const options1 = createImagesInfiniteOptions({
                collection_id: 'col-1',
                mode: 'normal',
                sort_by: sort1
            });
            const options2 = createImagesInfiniteOptions({
                collection_id: 'col-1',
                mode: 'normal',
                sort_by: sort2
            });
            expect(options1.queryKey).not.toEqual(options2.queryKey);
        });
    });

    describe('enabled', () => {
        it('is true for normal mode', () => {
            const options = createImagesInfiniteOptions({ collection_id: 'col-1', mode: 'normal' });
            expect(options.enabled).toBe(true);
        });

        it('is false for classifier mode without classifierSamples', () => {
            const options = createImagesInfiniteOptions({
                collection_id: 'col-1',
                mode: 'classifier'
            });
            expect(options.enabled).toBe(false);
        });

        it('is true for classifier mode with classifierSamples defined', () => {
            const options = createImagesInfiniteOptions({
                collection_id: 'col-1',
                mode: 'classifier',
                classifierSamples: { positiveSampleIds: [], negativeSampleIds: [] }
            });
            expect(options.enabled).toBe(true);
        });
    });

    describe('queryFn', () => {
        it('passes sort_by to readImages', async () => {
            const sort: SortFieldExpr[] = [
                { source: 'image', field_name: 'score', direction: 'desc', is_numeric: false }
            ];
            const options = createImagesInfiniteOptions({
                collection_id: 'col-1',
                mode: 'normal',
                sort_by: sort
            });

            await callQueryFn(options, { pageParam: 0, signal: new AbortController().signal });

            expect(readImagesMock).toHaveBeenCalledWith(
                expect.objectContaining({ body: expect.objectContaining({ sort_by: sort }) })
            );
        });

        it('passes sort_by as undefined when sort_by is null', async () => {
            const options = createImagesInfiniteOptions({
                collection_id: 'col-1',
                mode: 'normal',
                sort_by: null
            });

            await callQueryFn(options, { pageParam: 0, signal: new AbortController().signal });

            expect(readImagesMock).toHaveBeenCalledWith(
                expect.objectContaining({ body: expect.objectContaining({ sort_by: undefined }) })
            );
        });

        it('passes sort_by as undefined when sort_by is not provided', async () => {
            const options = createImagesInfiniteOptions({ collection_id: 'col-1', mode: 'normal' });

            await callQueryFn(options, { pageParam: 0, signal: new AbortController().signal });

            expect(readImagesMock).toHaveBeenCalledWith(
                expect.objectContaining({ body: expect.objectContaining({ sort_by: undefined }) })
            );
        });

        it('passes collection_id to readImages path', async () => {
            const options = createImagesInfiniteOptions({
                collection_id: 'col-42',
                mode: 'normal'
            });

            await callQueryFn(options, { pageParam: 0, signal: new AbortController().signal });

            expect(readImagesMock).toHaveBeenCalledWith(
                expect.objectContaining({ path: { collection_id: 'col-42' } })
            );
        });

        it('returns data from readImages response', async () => {
            const mockData = { data: [{ id: 'img-1' }], total_count: 1, nextCursor: null };
            readImagesMock.mockResolvedValue({ data: mockData });
            const options = createImagesInfiniteOptions({ collection_id: 'col-1', mode: 'normal' });

            const result = await callQueryFn(options, {
                pageParam: 0,
                signal: new AbortController().signal
            });

            expect(result).toBe(mockData);
        });
    });
});
