import { readDatasetOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';

export const useRootCollectionOptions = ({ collectionId }: { collectionId: string }) => {
    const options = readDatasetOptions({ path: { collection_id: collectionId } });
    const client = useQueryClient();

    const rootCollection = createQuery(options);

    const refetch = () => {
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    return {
        rootCollection,
        refetch
    };
};
