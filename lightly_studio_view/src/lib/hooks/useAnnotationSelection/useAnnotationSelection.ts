import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '../useGlobalStorage';

export function useAnnotationSelection() {
    const {
        context,
        setAnnotationId,
        setAnnotationLabel,
        setAnnotationType,
        setLastCreatedAnnotationId
    } = useAnnotationLabelContext();

    const { setStatus } = useSampleDetailsToolbarContext();
    const { updateLastAnnotationLabel } = useGlobalStorage();

    function selectAnnotation({
        annotationId,
        collectionId,
        annotations
    }: {
        annotationId: string;
        collectionId: string;
        annotations: AnnotationView[];
    }) {
        const annotation = annotations.find((a) => a.sample_id === annotationId);

        if (!annotation) return;

        if (
            annotation.annotation_type === 'instance_segmentation' ||
            annotation.annotation_type === 'semantic_segmentation'
        ) {
            setAnnotationType(annotation.annotation_type);
            setAnnotationLabel(annotation.annotation_label?.annotation_label_name ?? null);
            setStatus('brush');
        } else {
            setStatus('cursor');
        }

        if (annotation.annotation_label?.annotation_label_name)
            updateLastAnnotationLabel(
                collectionId,
                annotation.annotation_label!.annotation_label_name
            );

        setLastCreatedAnnotationId(null);
        setAnnotationId(context.annotationId === annotationId ? null : annotationId);
    }

    return {
        selectAnnotation
    };
}
