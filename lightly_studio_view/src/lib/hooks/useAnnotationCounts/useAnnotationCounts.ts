import { createQuery } from '@tanstack/svelte-query';
import { countAnnotationsByCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';
import { derived } from 'svelte/store';

type UseAnnotationCountsParams = {
    collectionId: string;
    options?: {
        filtered_labels?: string[];
        dimensions?: {
            min_width?: number;
            max_width?: number;
            min_height?: number;
            max_height?: number;
        };
    };
};

export const useAnnotationCounts = (params: StoreOrVal<UseAnnotationCountsParams>) => {
    const optionsStore = derived(toReadable(params), (currentParams) =>
        countAnnotationsByCollectionOptions({
            path: { collection_id: currentParams.collectionId },
            query: {
                ...(currentParams.options?.filtered_labels && {
                    filtered_labels: currentParams.options.filtered_labels
                }),
                ...(currentParams.options?.dimensions?.min_width && {
                    min_width: currentParams.options.dimensions.min_width
                }),
                ...(currentParams.options?.dimensions?.max_width && {
                    max_width: currentParams.options.dimensions.max_width
                }),
                ...(currentParams.options?.dimensions?.min_height && {
                    min_height: currentParams.options.dimensions.min_height
                }),
                ...(currentParams.options?.dimensions?.max_height && {
                    max_height: currentParams.options.dimensions.max_height
                })
            }
        })
    );
    return createQuery(optionsStore);
};
