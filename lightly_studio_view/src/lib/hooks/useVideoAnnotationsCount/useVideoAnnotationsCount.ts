import { createQuery } from '@tanstack/svelte-query';
import { countVideoFrameAnnotationsByVideoCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { type VideoCountAnnotationsFilter } from '$lib/api/lightly_studio_local';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';
import { derived } from 'svelte/store';

type UseVideoAnnotationCountsParams = {
    collectionId: string;
    filter: VideoCountAnnotationsFilter;
};

export const useVideoAnnotationCounts = (params: StoreOrVal<UseVideoAnnotationCountsParams>) => {
    const optionsStore = derived(toReadable(params), (currentParams) =>
        countVideoFrameAnnotationsByVideoCollectionOptions({
            path: { collection_id: currentParams.collectionId },
            body: {
                filter: currentParams.filter
            }
        })
    );
    return createQuery(optionsStore);
};
