import { render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import * as tanstackQuery from '@tanstack/svelte-query';
import { QueryClient } from '@tanstack/svelte-query';
import { get2dEmbeddingsStatusQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { get2dEmbeddingsStatus } from '$lib/api/lightly_studio_local/sdk.gen';
import { useRefetchEmbeddingPlotStatus, type useEmbeddingPlotStatus } from '$lib/hooks';
import UseEmbeddingPlotStatusTest from './UseEmbeddingPlotStatus.test.svelte';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    get2dEmbeddingsStatus: vi.fn()
}));

describe('useEmbeddingPlotStatus', () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('requests the status of the current collection', async () => {
        const embeddingCounts: Record<string, number> = { 'collection-a': 1, 'collection-b': 2 };
        vi.mocked(get2dEmbeddingsStatus).mockImplementation((async ({ path }) => ({
            data: { is_computed: false, embedding_count: embeddingCounts[path.collection_id] }
        })) as typeof get2dEmbeddingsStatus);
        const params = $state({ collectionId: 'collection-a' });
        let query!: ReturnType<typeof useEmbeddingPlotStatus>;
        render(UseEmbeddingPlotStatusTest, {
            queryClient: new QueryClient(),
            getCollectionId: () => params.collectionId,
            onQuery: (created) => (query = created)
        });
        await waitFor(() => expect(query.data?.embedding_count).toBe(1));

        params.collectionId = 'collection-b';

        await waitFor(() => expect(query.data?.embedding_count).toBe(2));
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
