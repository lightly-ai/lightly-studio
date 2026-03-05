import { readImageOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { ImageView } from '$lib/api/lightly_studio_local/types.gen';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';
import { derived, get } from 'svelte/store';

type UseImageParams = {
    sampleId: string;
};

export const useImage = (
    params: StoreOrVal<UseImageParams>
): { image: CreateQueryResult<ImageView, Error>; refetch: () => void } => {
    const paramsStore = toReadable(params);
    const optionsStore = derived(paramsStore, (currentParams) =>
        readImageOptions({
            path: {
                sample_id: currentParams.sampleId
            }
        })
    );
    const client = useQueryClient();
    const image = createQuery(optionsStore);
    const refetch = () => {
        client.invalidateQueries({ queryKey: get(optionsStore).queryKey });
    };

    return {
        refetch,
        image
    };
};
