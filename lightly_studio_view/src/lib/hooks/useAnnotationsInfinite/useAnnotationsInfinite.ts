import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import type { AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
import { toast } from 'svelte-sonner';
import { writable } from 'svelte/store';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { createAnnotationsInfiniteOptions } from './createAnnotationsInfiniteOptions';
import type { AnnotationsInfiniteParams } from './types';

export type { AnnotationsInfiniteParams } from './types';

export const useAnnotationsInfinite = (getParams: () => AnnotationsInfiniteParams) => {
    const isPending = writable(false);
    const annotations = createInfiniteQuery(() => createAnnotationsInfiniteOptions(getParams()));
    const client = useQueryClient();
    const refresh = () => {
        const options = createAnnotationsInfiniteOptions(getParams());
        client.invalidateQueries({ queryKey: options.queryKey });
        client.invalidateQueries({
            queryKey: useImageAnnotationCountsQueryKey
        });
    };

    const collection_id = getParams().collection_id;
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
