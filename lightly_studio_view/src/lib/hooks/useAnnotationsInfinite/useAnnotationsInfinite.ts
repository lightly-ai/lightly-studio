import {
    countAnnotationsByCollectionOptions,
    readAnnotationsWithPayloadInfiniteOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
import { toast } from 'svelte-sonner';
import type { AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import { writable } from 'svelte/store';

export const useAnnotationsInfinite = (
    ...props: Parameters<typeof readAnnotationsWithPayloadInfiniteOptions>
) => {
    const annotationsOptions = readAnnotationsWithPayloadInfiniteOptions(...props);
    const isPending = writable(false);
    const annotations = createInfiniteQuery({
        ...annotationsOptions,
        getNextPageParam: (lastPage) => {
            return lastPage.nextCursor || undefined;
        }
    });
    const client = useQueryClient();
    const refresh = () => {
        client.invalidateQueries({ queryKey: annotationsOptions.queryKey });
        client.invalidateQueries({
            queryKey: countAnnotationsByCollectionOptions({
                path: { collection_id: collection_id }
            }).queryKey
        });
    };

    const collection_id = props[0].path.collection_id;
    const { updateAnnotations } = useUpdateAnnotationsMutation({
        collectionId: collection_id
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
