import { afterEach, describe, expect, it, vi } from 'vitest';
import * as tanstackQuery from '@tanstack/svelte-query';
import { useEmbeddingPlotStatus, useRefetchEmbeddingPlotStatus } from '$lib/hooks';

describe('useEmbeddingPlotStatus', () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('queries the status route of the current collection', () => {
        const createQuerySpy = vi
            .spyOn(tanstackQuery, 'createQuery')
            .mockReturnValue({} as ReturnType<typeof tanstackQuery.createQuery>);
        let collectionId = 'collection-a';
        useEmbeddingPlotStatus(() => collectionId);
        const getOptions = createQuerySpy.mock.lastCall?.[0] as () => { queryKey: unknown };

        const [keyA] = getOptions().queryKey as [{ path: { collection_id: string } }];
        collectionId = 'collection-b';
        const [keyB] = getOptions().queryKey as [{ path: { collection_id: string } }];

        expect(keyA.path.collection_id).toBe('collection-a');
        expect(keyB.path.collection_id).toBe('collection-b');
    });

    it('refetches the status of the named collection', async () => {
        const refetchQueries = vi.fn(async () => undefined);
        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue({
            refetchQueries
        } as unknown as tanstackQuery.QueryClient);
        const refetchStatus = useRefetchEmbeddingPlotStatus();

        await refetchStatus('collection-a');

        const [{ queryKey }] = refetchQueries.mock.lastCall as unknown as [
            { queryKey: [{ path: { collection_id: string } }] }
        ];
        expect(queryKey[0].path.collection_id).toBe('collection-a');
    });
});
