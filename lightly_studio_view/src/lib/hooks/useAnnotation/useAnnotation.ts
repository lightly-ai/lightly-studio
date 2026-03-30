import { type AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import {
    getAnnotationOptions,
    readAnnotationLabelsOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { useUpdateAnnotationsMutation } from '../useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
import { useImageAnnotationCountsQueryKey } from '../useImageAnnotationCounts/useImageAnnotationCounts';

export const useAnnotation = ({
    collectionId,
    annotationId,
    onUpdate
}: {
    collectionId: string;
    annotationId: string;
    onUpdate?: () => void;
}) => {
    const annotationOptions = getAnnotationOptions({
        path: {
            annotation_id: annotationId,
            collection_id: collectionId
        }
    });
    const client = useQueryClient();

    const { updateAnnotations } = useUpdateAnnotationsMutation({
        collectionId
    });
    const annotation = createQuery(annotationOptions);

    const refetch = () => {
        client.invalidateQueries({ queryKey: annotationOptions.queryKey });
        client.invalidateQueries({
            queryKey: readAnnotationLabelsOptions({
                path: { collection_id: collectionId }
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
            onUpdate?.();
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
