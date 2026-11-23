import { afterEach, describe, expect, it, vi } from 'vitest';
import * as tanstackQuery from '@tanstack/svelte-query';
import { QueryClient } from '@tanstack/svelte-query';
import { get2dEmbeddingsStatusQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
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

    it('refetches the status of the named collection only', async () => {
        const client = new QueryClient();
        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue(client);
        const fetchStatus = vi.fn(async (collectionId: string) => ({ collectionId }));
        for (const collectionId of ['collection-a', 'collection-b']) {
            await client.fetchQuery({
                queryKey: get2dEmbeddingsStatusQueryKey({ path: { collection_id: collectionId } }),
                queryFn: () => fetchStatus(collectionId)
            });
        }

        await useRefetchEmbeddingPlotStatus()('collection-a');

        expect(fetchStatus.mock.calls).toEqual([
            ['collection-a'],
            ['collection-b'],
            ['collection-a']
        ]);
    });
});
