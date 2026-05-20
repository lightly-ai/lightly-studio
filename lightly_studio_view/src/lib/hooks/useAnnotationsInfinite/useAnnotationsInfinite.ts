import { readAnnotationsWithPayloadInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
import { toast } from 'svelte-sonner';
import type { AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import { writable } from 'svelte/store';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';

export const useAnnotationsInfinite = (
    getProps: () => Parameters<typeof readAnnotationsWithPayloadInfiniteOptions>[0]
) => {
    const isPending = writable(false);
    const annotations = createInfiniteQuery(() => ({
        ...readAnnotationsWithPayloadInfiniteOptions(getProps()),
        getNextPageParam: (lastPage) => {
            return lastPage.nextCursor || undefined;
        }
    }));
    const client = useQueryClient();
    const refresh = () => {
        const options = readAnnotationsWithPayloadInfiniteOptions(getProps());
        client.invalidateQueries({ queryKey: options.queryKey });
        client.invalidateQueries({
            queryKey: useImageAnnotationCountsQueryKey
        });
    };

    // collection_id is stable (from route), evaluate once at construction
    const collection_id = getProps().path.collection_id;
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
