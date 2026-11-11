import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

export function useAnnotationSelection() {
    const {
        context,
        setAnnotationId,
        setAnnotationLabel,
        setAnnotationType,
        setLastCreatedAnnotationId
    } = useAnnotationLabelContext();

    const { context: toolbarContext, setStatus } = useSampleDetailsToolbarContext();
    const { openSampleDetailsSidePanel } = useGlobalStorage();

    function selectAnnotation({
        annotationId,
        annotations
    }: {
        annotationId: string;
        collectionId: string;
        annotations: AnnotationView[];
    }) {
        const annotation = annotations.find((a) => a.sample_id === annotationId);

        if (!annotation) return;

        if (annotation.annotation_type === 'segmentation_mask') {
            setAnnotationType(annotation.annotation_type);
            setAnnotationLabel(annotation.annotation_label?.annotation_label_name ?? null);
            // Keep the active mask tool. Other tools switch to the brush.
            if (!['brush', 'slic', 'smart-select'].includes(toolbarContext.status)) {
                setStatus('brush');
            }
        } else {
            setStatus('cursor');
        }

        setLastCreatedAnnotationId(null);

        const isDeselecting = context.annotationId === annotationId;
        if (!isDeselecting) {
            openSampleDetailsSidePanel();
        }
        setAnnotationId(isDeselecting ? null : annotationId);
    }

    return {
        selectAnnotation
    };
}
