import * as tanstackQuery from '@tanstack/svelte-query';
import type { CreateQueryResult } from '@tanstack/svelte-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSimilarityRange } from './useSimilarityRange.svelte';

interface QueryOptions {
    queryKey: [{ path: unknown; body: unknown }];
}

describe('useSimilarityRange', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it('keys the query by collection and text embedding', () => {
        const createQuerySpy = vi
            .spyOn(tanstackQuery, 'createQuery')
            .mockReturnValue({} as CreateQueryResult);

        useSimilarityRange(() => ({ collectionId: 'col-1', textEmbedding: [0.1, 0.2] }));
        const options = createQuerySpy.mock.lastCall?.[0]() as unknown as QueryOptions;

        expect(options.queryKey[0].path).toEqual({ collection_id: 'col-1' });
        expect(options.queryKey[0].body).toEqual({ text_embedding: [0.1, 0.2] });
    });
});
