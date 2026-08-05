import {
    createAnnotationLabelsBatchMutation,
    readAnnotationLabelsWithCountsOptions,
    readAnnotationLabelsWithCountsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';

export function useClasses(getParams: () => { collectionId: string; enabled: boolean }) {
    const client = useQueryClient();
    const query = createQuery(() => ({
        ...readAnnotationLabelsWithCountsOptions({
            path: { collection_id: getParams().collectionId }
        }),
        enabled: getParams().enabled
    }));
    const addMutation = createMutation(() => createAnnotationLabelsBatchMutation());

    const refresh = () =>
        client.invalidateQueries({
            queryKey: readAnnotationLabelsWithCountsQueryKey({
                path: { collection_id: getParams().collectionId }
            })
        });
    const addClasses = async (names: string[]) => {
        await addMutation.mutateAsync({
            path: { collection_id: getParams().collectionId },
            body: { annotation_label_names: names }
        });
        await refresh();
    };

    return { query, addClasses };
}
