import { describe, expect, it, vi } from 'vitest';
import type { SortFieldExpr } from '$lib/api/lightly_studio_local';
import type { QueryClient, CreateInfiniteQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { useImagesInfinite } from './useImagesInfinite';

const readImagesMock = vi.fn();

vi.mock('$lib/api/lightly_studio_local', () => ({
    readImages: (...args: unknown[]) => readImagesMock(...args)
}));

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [])
}));

describe('useImagesInfinite', () => {
    const mockInvalidateQueries = vi.fn();
    const mockQueryClient: Pick<QueryClient, 'invalidateQueries'> = {
        invalidateQueries: mockInvalidateQueries
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let capturedOptions: any;

    beforeEach(() => {
        vi.resetAllMocks();
        capturedOptions = undefined;

        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue(mockQueryClient as QueryClient);
        vi.spyOn(tanstackQuery, 'createInfiniteQuery').mockImplementation((options) => {
            capturedOptions = options;
            return {
                subscribe: (fn: (value: unknown) => void) => {
                    fn({});
                    return vi.fn();
                }
            } as CreateInfiniteQueryResult<unknown, Error>;
        });

        readImagesMock.mockResolvedValue({ data: { data: [], total_count: 0, nextCursor: null } });
    });

    describe('sort_by in query key', () => {
        it('includes sort_by in the query key when provided', () => {
            const sort: SortFieldExpr[] = [
                { source: 'image', field_name: 'score', direction: 'desc', is_numeric: false }
            ];

            useImagesInfinite({ collection_id: 'coll-1', mode: 'normal', sort_by: sort });

            expect(capturedOptions.queryKey).toContain(sort);
        });

        it('includes null in the query key when sort_by is null', () => {
            useImagesInfinite({ collection_id: 'coll-1', mode: 'normal', sort_by: null });

            expect(capturedOptions.queryKey).toContain(null);
        });

        it('produces different query keys for different sort_by values', () => {
            const sort1: SortFieldExpr[] = [
                { source: 'image', field_name: 'score', direction: 'desc', is_numeric: false }
            ];
            const sort2: SortFieldExpr[] = [
                { source: 'image', field_name: 'filename', direction: 'asc', is_numeric: false }
            ];

            useImagesInfinite({ collection_id: 'coll-1', mode: 'normal', sort_by: sort1 });
            const queryKey1 = capturedOptions.queryKey;

            useImagesInfinite({ collection_id: 'coll-1', mode: 'normal', sort_by: sort2 });
            const queryKey2 = capturedOptions.queryKey;

            expect(queryKey1).not.toEqual(queryKey2);
        });
    });

    describe('sort_by in request body', () => {
        it('passes sort_by to readImages when provided', async () => {
            const sort: SortFieldExpr[] = [
                { source: 'image', field_name: 'score', direction: 'desc', is_numeric: false }
            ];

            useImagesInfinite({ collection_id: 'coll-1', mode: 'normal', sort_by: sort });

            await capturedOptions.queryFn({ pageParam: 0, signal: new AbortController().signal });

            expect(readImagesMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: expect.objectContaining({ sort_by: sort })
                })
            );
        });

        it('passes sort_by as undefined to readImages when sort_by is null', async () => {
            useImagesInfinite({ collection_id: 'coll-1', mode: 'normal', sort_by: null });

            await capturedOptions.queryFn({ pageParam: 0, signal: new AbortController().signal });

            expect(readImagesMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: expect.objectContaining({ sort_by: undefined })
                })
            );
        });

        it('passes sort_by as undefined to readImages when sort_by is not provided', async () => {
            useImagesInfinite({ collection_id: 'coll-1', mode: 'normal' });

            await capturedOptions.queryFn({ pageParam: 0, signal: new AbortController().signal });

            expect(readImagesMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: expect.objectContaining({ sort_by: undefined })
                })
            );
        });
    });
});
