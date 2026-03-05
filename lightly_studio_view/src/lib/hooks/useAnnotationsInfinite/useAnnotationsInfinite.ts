import {
    countAnnotationsByCollectionOptions,
    readAnnotationsWithPayloadInfiniteOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
import { toast } from 'svelte-sonner';
import type { AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import { derived, get, writable } from 'svelte/store';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';

type UseAnnotationsInfiniteParams = Parameters<typeof readAnnotationsWithPayloadInfiniteOptions>[0];

export const useAnnotationsInfinite = (params: StoreOrVal<UseAnnotationsInfiniteParams>) => {
    const paramsStore = toReadable(params);
    const optionsStore = derived(paramsStore, (currentParams) => {
        const annotationsOpts = readAnnotationsWithPayloadInfiniteOptions(currentParams);
        return {
            ...annotationsOpts,
            getNextPageParam: (lastPage: { nextCursor?: number | null }) => {
                return lastPage.nextCursor ?? undefined;
            }
        };
    });

    const isPending = writable(false);
    const annotations = createInfiniteQuery(optionsStore);
    const client = useQueryClient();

    const refresh = () => {
        const currentParams = get(paramsStore);
        client.invalidateQueries({ queryKey: get(optionsStore).queryKey });
        client.invalidateQueries({
            queryKey: countAnnotationsByCollectionOptions({
                path: { collection_id: currentParams.path.collection_id }
            }).queryKey
        });
    };

    const collectionIdStore = derived(
        paramsStore,
        (currentParams) => currentParams.path.collection_id
    );

    const { updateAnnotations } = useUpdateAnnotationsMutation({
        collectionId: get(collectionIdStore)
    });

    return {
        annotations,
        refresh,
        isPending,
        updateAnnotations: async (inputs: AnnotationUpdateInput[]) => {
            try {
                isPending.set(true);
                await updateAnnotations(inputs);
                refresh();
                toast.success('Annotations updated successfully');
            } catch (error: unknown) {
                toast.error('Failed to update annotations:' + (error as Error).message);
            } finally {
                isPending.set(false);
            }
        }
    };
};
