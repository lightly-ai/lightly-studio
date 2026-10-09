import { describe, expect, it, vi } from 'vitest';
import * as tanstackQuery from '@tanstack/svelte-query';
import type { CreateQueryOptions, CreateQueryResult } from '@tanstack/svelte-query';
import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useEmbeddings } from './useEmbeddings';

describe('useEmbeddings', () => {
    it('requests the projection onto the given axes', () => {
        const createQuerySpy = vi
            .spyOn(tanstackQuery, 'createQuery')
            .mockReturnValue({} as CreateQueryResult);
        const axes = { x: [1, 0], y: [0, 1] };

        useEmbeddings('collection-id', null, null, axes);

        const options = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        expect(options.queryKey).toEqual(
            get2dEmbeddingsOptions({
                path: { collection_id: 'collection-id' },
                body: { filters: {}, color_by: null, axes }
            }).queryKey
        );
    });
});
