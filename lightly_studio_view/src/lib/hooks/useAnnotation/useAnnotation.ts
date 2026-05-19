import { type AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import {
    getAnnotationOptions,
    readAnnotationLabelsOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { useUpdateAnnotationsMutation } from '../useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
import { useImageAnnotationCountsQueryKey } from '../useImageAnnotationCounts/useImageAnnotationCounts';

export const useAnnotation = (
    getParams: () => {
        collectionId: string;
        annotationId: string;
        onUpdate?: () => void;
        enabled?: boolean;
    }
) => {
    const client = useQueryClient();

    // Evaluate collectionId once at construction for mutation setup (stable route param)
    const { updateAnnotations } = useUpdateAnnotationsMutation({
        collectionId: getParams().collectionId
    });

    const annotation = createQuery(() => ({
        ...getAnnotationOptions({
            path: {
                annotation_id: getParams().annotationId,
                collection_id: getParams().collectionId
            }
        }),
        enabled: getParams().enabled ?? true
    }));

    const refetch = () => {
        const params = getParams();
        client.invalidateQueries({
            queryKey: getAnnotationOptions({
                path: {
                    annotation_id: params.annotationId,
                    collection_id: params.collectionId
                }
            }).queryKey
        });
        client.invalidateQueries({
            queryKey: readAnnotationLabelsOptions({
                path: { collection_id: params.collectionId }
            }).queryKey
        });
        client.invalidateQueries({
            queryKey: useImageAnnotationCountsQueryKey
        });
    };

    const updateAnnotation = async (input: AnnotationUpdateInput) => {
        try {
            await updateAnnotations([input]);
            refetch();
            toast.success('Annotation updated successfully');
            getParams().onUpdate?.();
        } catch (error: unknown) {
            toast.error('Failed to update annotation:' + (error as Error).message);
        }
    };
    return {
        updateAnnotation,
        annotation,
        refetch
    };
};
