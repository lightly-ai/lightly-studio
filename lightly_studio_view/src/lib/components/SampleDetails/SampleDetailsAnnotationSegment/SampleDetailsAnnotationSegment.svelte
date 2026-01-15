<script lang="ts">
    import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
    import { Segment } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import SampleDetailsSidePanelAnnotation from '../SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { addAnnotationDeleteToUndoStack } from '$lib/services/addAnnotationDeleteToUndoStack';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { toast } from 'svelte-sonner';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';

    type SampleDetailsAnnotationSegmentProps = {
        annotationsIdsToHide: Set<string>;
        collectionId: string;
        annotations: AnnotationView[];
        isPanModeEnabled: boolean;
        refetch: () => void;
    };

    let {
        annotationsIdsToHide = $bindable<Set<string>>(),
        collectionId,
        annotations,
        isPanModeEnabled,
        refetch
    }: SampleDetailsAnnotationSegmentProps = $props();

    const { addReversibleAction } = useGlobalStorage();

    const {
        context: annotationLabelContext,
        setAnnotationId,
        setAnnotationLabel,
        setLastCreatedAnnotationId,
        setAnnotationType
    } = useAnnotationLabelContext();
    const { setStatus } = useSampleDetailsToolbarContext();

    const annotationLabels = useAnnotationLabels({ collectionId });
    const { createAnnotation } = useCreateAnnotation({
        collectionId
    });
    const { deleteAnnotation } = useDeleteAnnotation({
        collectionId
    });

    const annotationsSort = $derived.by(() => {
        return annotations
            ? [...annotations]
                  .filter(
                      (annotation) => annotation.annotation_type !== AnnotationType.CLASSIFICATION
                  )
                  .sort((a, b) =>
                      a.annotation_label.annotation_label_name.localeCompare(
                          b.annotation_label?.annotation_label_name
                      )
                  )
            : [];
    });

    const toggleAnnotationSelection = (annotationId: string) => {
        if (isPanModeEnabled) return;
        const annotation = annotations?.find((a) => a.sample_id === annotationId);

        if (!annotation) return;

        if (annotation.annotation_type === 'instance_segmentation') {
            setAnnotationType(annotation.annotation_type);
            setStatus('brush');

            setAnnotationLabel(annotation.annotation_label?.annotation_label_name);
        }

        setLastCreatedAnnotationId(null);
        annotationLabelContext.annotationId =
            annotationLabelContext.annotationId === annotationId ? null : annotationId;
    };

    const handleDeleteAnnotation = async (annotationId: string) => {
        if (!$annotationLabels.data) return;

        const annotation = annotations?.find((a) => a.sample_id === annotationId);
        if (!annotation) return;

        const _delete = async () => {
            try {
                addAnnotationDeleteToUndoStack({
                    annotation,
                    labels: $annotationLabels.data!,
                    addReversibleAction,
                    createAnnotation,
                    refetch
                });

                await deleteAnnotation(annotationId);
                toast.success('Annotation deleted successfully');
                refetch();
                if (annotationLabelContext.annotationId === annotationId) {
                    setAnnotationId(null);
                }
            } catch (error) {
                toast.error('Failed to delete annotation. Please try again.');
                console.error('Error deleting annotation:', error);
            }
        };
        _delete();
    };

    const onToggleShowAnnotation = (annotationId: string) => {
        annotationsIdsToHide = new Set(
            annotationsIdsToHide.has(annotationId)
                ? [...annotationsIdsToHide].filter((id) => id !== annotationId)
                : [...annotationsIdsToHide, annotationId]
        );
    };
</script>

<Segment title="Annotations">
    <div class="flex flex-col gap-2">
        {#each annotationsSort as annotation}
            <SampleDetailsSidePanelAnnotation
                {annotation}
                isSelected={annotationLabelContext.annotationId === annotation.sample_id}
                onClick={() => toggleAnnotationSelection(annotation.sample_id)}
                onDeleteAnnotation={() => handleDeleteAnnotation(annotation.sample_id)}
                isHidden={annotationsIdsToHide.has(annotation.sample_id)}
                onToggleShowAnnotation={(e) => {
                    e.stopPropagation();
                    onToggleShowAnnotation(annotation.sample_id);
                }}
                onUpdate={refetch}
                onChangeAnnotationLabel={(newLabel) => {
                    // The annotation label is always the last selected label.
                    setAnnotationLabel(newLabel);

                    setLastCreatedAnnotationId(null);

                    if (
                        annotationLabelContext.annotationType ===
                        AnnotationType.INSTANCE_SEGMENTATION
                    ) {
                        setAnnotationId(annotation.sample_id);
                    }
                }}
                canHighlight={annotationLabelContext.lastCreatedAnnotationId ===
                    annotation.sample_id}
                onClickSelectList={() => {
                    annotationLabelContext.annotationId = annotation.sample_id;
                }}
            />
        {/each}
    </div>
</Segment>
