import { readAnnotationLabelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { isReadableStore } from '$lib/hooks/utils/isReadableStore';
import { createQuery } from '@tanstack/svelte-query';
import { derived, type Readable } from 'svelte/store';

type UseAnnotationLabelsParams = {
    collectionId: string;
    enabled?: boolean;
};

const createAnnotationLabelsQueryOptions = ({
    collectionId,
    enabled
}: UseAnnotationLabelsParams) => {
    return {
        ...readAnnotationLabelsOptions({
            path: { collection_id: collectionId }
        }),
        enabled
    };
};

export const useAnnotationLabels = (
    paramsInput: UseAnnotationLabelsParams | Readable<UseAnnotationLabelsParams>
) => {
    const options = isReadableStore<UseAnnotationLabelsParams>(paramsInput)
        ? derived(paramsInput, ($params) => createAnnotationLabelsQueryOptions($params))
        : createAnnotationLabelsQueryOptions(paramsInput);

    return createQuery(options);
};
