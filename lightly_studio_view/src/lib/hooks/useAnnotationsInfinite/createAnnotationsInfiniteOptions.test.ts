import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAnnotationsInfiniteOptions } from './createAnnotationsInfiniteOptions';

type Options = ReturnType<typeof createAnnotationsInfiniteOptions>;
type QueryFnContext = { pageParam: number; signal: AbortSignal };

const callQueryFn = (options: Options, ctx: QueryFnContext) => {
    const fn = options.queryFn as (ctx: QueryFnContext) => Promise<unknown>;
    return fn(ctx);
};

const { readAnnotationsWithPayloadMock } = vi.hoisted(() => ({
    readAnnotationsWithPayloadMock: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', () => ({
    readAnnotationsWithPayload: (...args: unknown[]) => readAnnotationsWithPayloadMock(...args)
}));

describe('createAnnotationsInfiniteOptions', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        readAnnotationsWithPayloadMock.mockResolvedValue({
            data: { data: [], total_count: 0, nextCursor: null }
        });
    });

    describe('query key', () => {
        it('includes collection_id', () => {
            const options = createAnnotationsInfiniteOptions({ collection_id: 'col-1' });
            expect(options.queryKey[1]).toBe('col-1');
        });

        it('puts filters in query key', () => {
            const filters = {
                annotation_label_ids: ['lbl-1'],
                tag_ids: ['t1'],
                sample_ids: ['s1'],
                text_embedding: [0.1, 0.2]
            };
            const options = createAnnotationsInfiniteOptions({
                collection_id: 'col-1',
                ...filters
            });
            expect(options.queryKey[2]).toEqual(filters);
        });

        it('produces different keys for different text_embedding values', () => {
            const options1 = createAnnotationsInfiniteOptions({
                collection_id: 'col-1',
                text_embedding: [0.1]
            });
            const options2 = createAnnotationsInfiniteOptions({
                collection_id: 'col-1',
                text_embedding: [0.2]
            });
            expect(options1.queryKey).not.toEqual(options2.queryKey);
        });

        it('produces different keys for different sample_ids values', () => {
            const options1 = createAnnotationsInfiniteOptions({
                collection_id: 'col-1',
                sample_ids: ['s1']
            });
            const options2 = createAnnotationsInfiniteOptions({
                collection_id: 'col-1',
                sample_ids: ['s2']
            });
            expect(options1.queryKey).not.toEqual(options2.queryKey);
        });

        it('produces different keys for different embedding_region values', () => {
            const options1 = createAnnotationsInfiniteOptions({
                collection_id: 'col-1',
                embedding_region: { polygon: [{ x: 0, y: 0 }] }
            });
            const options2 = createAnnotationsInfiniteOptions({
                collection_id: 'col-1',
                embedding_region: { polygon: [{ x: 1, y: 1 }] }
            });
            expect(options1.queryKey).not.toEqual(options2.queryKey);
        });
    });

    describe('pagination', () => {
        it('uses nextCursor as next page param', () => {
            const options = createAnnotationsInfiniteOptions({ collection_id: 'col-1' });
            expect(options.getNextPageParam?.({ nextCursor: 20 } as never, [], 0, [])).toBe(20);
        });

        it('returns undefined when nextCursor is null', () => {
            const options = createAnnotationsInfiniteOptions({ collection_id: 'col-1' });
            expect(
                options.getNextPageParam?.({ nextCursor: null } as never, [], 0, [])
            ).toBeUndefined();
        });
    });

    describe('queryFn', () => {
        it('passes collection_id to readAnnotationsWithPayload path', async () => {
            const options = createAnnotationsInfiniteOptions({ collection_id: 'col-42' });

            await callQueryFn(options, { pageParam: 0, signal: new AbortController().signal });

            expect(readAnnotationsWithPayloadMock).toHaveBeenCalledWith(
                expect.objectContaining({ path: { collection_id: 'col-42' } })
            );
        });

        it('passes pageParam as cursor and uses default limit', async () => {
            const options = createAnnotationsInfiniteOptions({ collection_id: 'col-1' });

            await callQueryFn(options, { pageParam: 20, signal: new AbortController().signal });

            expect(readAnnotationsWithPayloadMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: expect.objectContaining({
                        pagination: { cursor: 20, limit: 100 }
                    })
                })
            );
        });

        it('passes filters to readAnnotationsWithPayload body', async () => {
            const options = createAnnotationsInfiniteOptions({
                collection_id: 'col-1',
                annotation_label_ids: ['lbl-1'],
                tag_ids: ['t1'],
                sample_ids: ['s1'],
                text_embedding: [0.5, 0.5]
            });

            await callQueryFn(options, { pageParam: 0, signal: new AbortController().signal });

            expect(readAnnotationsWithPayloadMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: {
                        pagination: { cursor: 0, limit: 100 },
                        annotation_label_ids: ['lbl-1'],
                        tag_ids: ['t1'],
                        sample_ids: ['s1'],
                        text_embedding: [0.5, 0.5]
                    }
                })
            );
        });

        it('passes the embedding region geometry to readAnnotationsWithPayload body', async () => {
            const embedding_region = {
                polygon: [
                    { x: 0, y: 0 },
                    { x: 1, y: 0 },
                    { x: 1, y: 1 }
                ]
            };
            const options = createAnnotationsInfiniteOptions({
                collection_id: 'col-1',
                embedding_region
            });

            await callQueryFn(options, { pageParam: 0, signal: new AbortController().signal });

            expect(readAnnotationsWithPayloadMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: expect.objectContaining({ embedding_region })
                })
            );
        });

        it('returns data from readAnnotationsWithPayload response', async () => {
            const mockData = {
                data: [{ annotation: { sample_id: 'ann-1' } }],
                total_count: 1,
                nextCursor: null
            };
            readAnnotationsWithPayloadMock.mockResolvedValue({ data: mockData });
            const options = createAnnotationsInfiniteOptions({ collection_id: 'col-1' });

            const result = await callQueryFn(options, {
                pageParam: 0,
                signal: new AbortController().signal
            });

            expect(result).toBe(mockData);
        });
    });
});
