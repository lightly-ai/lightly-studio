import { SampleType, type AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import {
    countAnnotationsByDatasetOptions,
    getAnnotationWithPayloadOptions,
    readAnnotationLabelsOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { useUpdateAnnotationsMutation } from '../useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';

export const useAnnotationDetails = ({
    datasetId,
    annotationId,
    onUpdate
}: {
    datasetId: string;
    annotationId: string;
    onUpdate?: () => void;
    sampleType?: SampleType;
}) => {
    const annotationOptions = getAnnotationWithPayloadOptions({
        path: {
            sample_id: annotationId
        }
    });
    const client = useQueryClient();

    const { updateAnnotations } = useUpdateAnnotationsMutation({
        datasetId
    });
    const annotation = createQuery(annotationOptions);

    const refetch = () => {
        client.invalidateQueries({ queryKey: annotationOptions.queryKey });
        client.invalidateQueries({
            queryKey: readAnnotationLabelsOptions({
                path: { dataset_id: datasetId }
            }).queryKey
        });
        client.invalidateQueries({
            queryKey: countAnnotationsByDatasetOptions({
                path: { dataset_id: datasetId }
            }).queryKey
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
