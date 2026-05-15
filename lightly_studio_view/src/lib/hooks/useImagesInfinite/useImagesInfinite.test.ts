import { describe, expect, it, vi, beforeEach } from 'vitest';
import type { QueryClient, CreateInfiniteQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { useImagesInfinite } from './useImagesInfinite';

vi.mock('$lib/api/lightly_studio_local', () => ({
    readImages: vi.fn()
}));

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [])
}));

describe('useImagesInfinite', () => {
    const mockInvalidateQueries = vi.fn();
    const mockQueryClient: Pick<QueryClient, 'invalidateQueries'> = {
        invalidateQueries: mockInvalidateQueries
    };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue(mockQueryClient as QueryClient);
        vi.spyOn(tanstackQuery, 'createInfiniteQuery').mockReturnValue({
            subscribe: (fn: (value: unknown) => void) => {
                fn({});
                return vi.fn();
            }
        } as CreateInfiniteQueryResult<unknown, Error>);
    });

    it('calls invalidateQueries with the correct key on refresh', () => {
        const { refresh } = useImagesInfinite({ collection_id: 'coll-1', mode: 'normal' });

        refresh();

        expect(mockInvalidateQueries).toHaveBeenCalledWith(
            expect.objectContaining({
                queryKey: expect.arrayContaining(['readImagesInfinite', 'coll-1'])
            })
        );
    });
});
