import { readAnnotationLabelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';
import { createQuery } from '@tanstack/svelte-query';
import { derived } from 'svelte/store';

type UseAnnotationLabelsParams = {
    collectionId: string;
};

export const useAnnotationLabels = (params: StoreOrVal<UseAnnotationLabelsParams>) => {
    const optionsStore = derived(toReadable(params), ($p) =>
        readAnnotationLabelsOptions({
            path: { collection_id: $p.collectionId }
        })
    );
    return createQuery(optionsStore);
};
