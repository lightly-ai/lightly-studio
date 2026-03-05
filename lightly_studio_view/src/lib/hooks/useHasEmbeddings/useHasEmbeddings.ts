import { hasEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import { derived } from 'svelte/store';

type UseHasEmbeddingsParams = {
    collectionId: string;
};

export const useHasEmbeddings = (
    params: StoreOrVal<UseHasEmbeddingsParams>
): CreateQueryResult<boolean, Error> => {
    const optionsStore = derived(toReadable(params), ($p) =>
        hasEmbeddingsOptions({
            path: { collection_id: $p.collectionId }
        })
    );
    return createQuery(optionsStore);
};
