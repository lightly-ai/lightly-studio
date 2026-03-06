import { hasEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { isReadableStore } from '$lib/hooks/utils/isReadableStore';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import { derived, type Readable } from 'svelte/store';

type UseHasEmbeddingsParams = {
    collectionId: string;
    enabled?: boolean;
};

const createHasEmbeddingsQueryOptions = ({
    collectionId,
    enabled
}: UseHasEmbeddingsParams) => {
    return {
        ...hasEmbeddingsOptions({
            path: { collection_id: collectionId }
        }),
        enabled
    };
};

export const useHasEmbeddings = (
    paramsInput: UseHasEmbeddingsParams | Readable<UseHasEmbeddingsParams>
): CreateQueryResult<boolean, Error> => {
    const options = isReadableStore<UseHasEmbeddingsParams>(paramsInput)
        ? derived(paramsInput, ($params) => createHasEmbeddingsQueryOptions($params))
        : createHasEmbeddingsQueryOptions(paramsInput);

    return createQuery(options);
};
