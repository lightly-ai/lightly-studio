import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateInfiniteQueryResult, QueryClient } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { get } from 'svelte/store';
import type { useMcapSequencesInfinite } from './';
import UseMcapSequencesInfiniteHarness from './UseMcapSequencesInfiniteHarness.svelte';

describe('useMcapSequencesInfinite', () => {
    const invalidateQueries = vi.fn();
    const firstPage = {
        data: [{ sample_id: 'sequence-1', sample_count: 3 }],
        total_count: 2,
        nextCursor: 1
    };
    const secondPage = {
        data: [{ sample_id: 'sequence-2', sample_count: 1 }],
        total_count: 2,
        nextCursor: null
    };
    const query = {
        data: { pages: [firstPage], pageParams: [undefined] },
        isSuccess: true,
        hasNextPage: true,
        isFetchingNextPage: false,
        fetchNextPage: vi.fn()
    };

    const renderHook = () => {
        let result: ReturnType<typeof useMcapSequencesInfinite> | undefined;
        render(UseMcapSequencesInfiniteHarness, {
            collectionId: 'collection-1',
            onReady: (hookResult) => {
                result = hookResult;
            }
        });
        flushSync();
        if (!result) throw new Error('useMcapSequencesInfinite did not initialize');
        return result;
    };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue({
            invalidateQueries
        } as Pick<QueryClient, 'invalidateQueries'> as QueryClient);
        vi.spyOn(tanstackQuery, 'createInfiniteQuery').mockReturnValue(
            query as unknown as CreateInfiniteQueryResult<unknown, Error>
        );
    });

    it('exposes flattened sequences and their total count', () => {
        const { data, totalCount } = renderHook();

        expect(get(data)).toEqual(firstPage.data);
        expect(get(totalCount)).toBe(2);
    });

    it('loads the next page only when the query can do so', () => {
        const { loadMore } = renderHook();
        loadMore();
        expect(query.fetchNextPage).toHaveBeenCalledOnce();
    });

    it('flattens sequences from every loaded page', () => {
        vi.spyOn(tanstackQuery, 'createInfiniteQuery').mockReturnValue({
            ...query,
            data: { pages: [firstPage, secondPage], pageParams: [undefined, 1] }
        } as unknown as CreateInfiniteQueryResult<unknown, Error>);

        const { data } = renderHook();

        expect(get(data)).toEqual([...firstPage.data, ...secondPage.data]);
    });
});
