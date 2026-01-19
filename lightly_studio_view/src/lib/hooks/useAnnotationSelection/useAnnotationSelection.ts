import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import type { AnnotationView } from '$lib/api/lightly_studio_local';

export function useAnnotationSelection() {
    const {
        context,
        setAnnotationId,
        setAnnotationLabel,
        setAnnotationType,
        setLastCreatedAnnotationId
    } = useAnnotationLabelContext();

    const { setStatus } = useSampleDetailsToolbarContext();

    function selectAnnotation({
        annotationId,
        annotations
    }: {
        annotationId: string;
        annotations: AnnotationView[];
    }) {
        const annotation = annotations.find((a) => a.sample_id === annotationId);

        if (!annotation) return;

        if (annotation.annotation_type === 'instance_segmentation') {
            setAnnotationType(annotation.annotation_type);
            setAnnotationLabel(annotation.annotation_label?.annotation_label_name ?? null);
            setStatus('brush');
        } else {
            setStatus('cursor');
        }

        setLastCreatedAnnotationId(null);

        setAnnotationId(context.annotationId === annotationId ? null : annotationId);
    }

    return {
        selectAnnotation
    };
}
