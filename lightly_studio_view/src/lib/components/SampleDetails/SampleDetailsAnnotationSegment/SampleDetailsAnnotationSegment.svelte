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
    import { useAnnotationSelection } from '$lib/hooks/useAnnotationSelection/useAnnotationSelection';

    type SampleDetailsAnnotationSegmentProps = {
        annotationsIdsToHide: Set<string>;
        collectionId: string;
        annotations: AnnotationView[];
        isPanModeEnabled: boolean;
        refetch: () => void;
    };

    let {
        annotationsIdsToHide = $bindable<Set<string>>(new Set()),
        collectionId,
        annotations,
        isPanModeEnabled,
        refetch
    }: SampleDetailsAnnotationSegmentProps = $props();

    const { addReversibleAction, updateLastAnnotationLabel } = useGlobalStorage();

    const {
        context: annotationLabelContext,
        setAnnotationId,
        setAnnotationLabel,
        setLastCreatedAnnotationId,
        setLockedAnnotationIds
    } = useAnnotationLabelContext();

    const annotationLabels = useAnnotationLabels({ collectionId });
    const { createAnnotation } = useCreateAnnotation({
        collectionId
    });
    const { deleteAnnotation } = useDeleteAnnotation({
        collectionId
    });
    const { selectAnnotation } = useAnnotationSelection();

    const nonClassificationAnnotations = $derived.by(() =>
        annotations
            ? annotations.filter(
                  (annotation) => annotation.annotation_type !== AnnotationType.CLASSIFICATION
              )
            : []
    );

    let orderedAnnotations = $state<AnnotationView[]>([]);
    let draggedAnnotationId = $state<string | null>(null);
    let dragOverAnnotationId = $state<string | null>(null);

    $effect(() => {
        orderedAnnotations = [...nonClassificationAnnotations];
    });

    const toggleAnnotationSelection = (annotationId: string) => {
        if (isPanModeEnabled) return;

        selectAnnotation({ annotationId, annotations, collectionId });
    };

    const toggleAnnotationLock = (annotationId: string) => {
        let lockers = annotationLabelContext.lockedAnnotationIds ?? new Set([annotationId]);
        if (lockers) {
            if (lockers.has(annotationId)) {
                lockers.delete(annotationId);
            } else {
                lockers.add(annotationId);
            }
        }

        setLockedAnnotationIds(new Set(lockers));
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

    const reorderAnnotationLayers = async (orderedAnnotationIds: string[]) => {
        const parentSampleId = nonClassificationAnnotations[0]?.parent_sample_id;
        if (!parentSampleId) return;

        const response = await fetch(`/api/collections/${collectionId}/annotations/layers/reorder`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sample_id: parentSampleId,
                ordered_annotation_ids: orderedAnnotationIds
            })
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }
    };

    const handleDragStart = (event: DragEvent, annotationId: string) => {
        draggedAnnotationId = annotationId;
        dragOverAnnotationId = null;
        event.dataTransfer?.setData('text/plain', annotationId);
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = 'move';
        }
    };

    const handleDragOver = (event: DragEvent, annotationId: string) => {
        if (!draggedAnnotationId || draggedAnnotationId === annotationId) {
            return;
        }
        event.preventDefault();
        dragOverAnnotationId = annotationId;
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = 'move';
        }
    };

    const handleDragEnd = () => {
        draggedAnnotationId = null;
        dragOverAnnotationId = null;
    };

    const handleDrop = async (event: DragEvent, targetAnnotationId: string) => {
        event.preventDefault();

        if (!draggedAnnotationId || draggedAnnotationId === targetAnnotationId) {
            handleDragEnd();
            return;
        }

        const previousOrder = [...orderedAnnotations];
        const draggedIndex = previousOrder.findIndex((item) => item.sample_id === draggedAnnotationId);
        const targetIndex = previousOrder.findIndex((item) => item.sample_id === targetAnnotationId);
        if (draggedIndex === -1 || targetIndex === -1) {
            handleDragEnd();
            return;
        }

        const nextOrder = [...previousOrder];
        const [draggedAnnotation] = nextOrder.splice(draggedIndex, 1);
        nextOrder.splice(targetIndex, 0, draggedAnnotation);
        orderedAnnotations = nextOrder;
        handleDragEnd();

        try {
            await reorderAnnotationLayers(nextOrder.map((item) => item.sample_id));
            refetch();
        } catch (error) {
            orderedAnnotations = previousOrder;
            toast.error('Failed to reorder annotation layers. Please try again.');
            console.error('Error reordering annotation layers:', error);
        }
    };
</script>

<Segment title="Annotations">
    <div class="flex flex-col gap-2">
        {#each orderedAnnotations as annotation, index}
            <div
                class="rounded-sm transition-colors"
                class:ring-1={dragOverAnnotationId === annotation.sample_id}
                class:ring-primary={dragOverAnnotationId === annotation.sample_id}
                class:opacity-70={draggedAnnotationId === annotation.sample_id}
                role="listitem"
                aria-grabbed={draggedAnnotationId === annotation.sample_id}
                draggable={!isPanModeEnabled && orderedAnnotations.length > 1}
                ondragstart={(event) => handleDragStart(event, annotation.sample_id)}
                ondragover={(event) => handleDragOver(event, annotation.sample_id)}
                ondrop={(event) => handleDrop(event, annotation.sample_id)}
                ondragend={handleDragEnd}
            >
                <SampleDetailsSidePanelAnnotation
                    {annotation}
                    position={orderedAnnotations.length - index}
                    isSelected={annotationLabelContext.annotationId === annotation.sample_id}
                    onClick={() => toggleAnnotationSelection(annotation.sample_id)}
                    onDeleteAnnotation={() => handleDeleteAnnotation(annotation.sample_id)}
                    isHidden={annotationsIdsToHide.has(annotation.sample_id)}
                    isLocked={annotationLabelContext.lockedAnnotationIds?.has(annotation.sample_id) ??
                        false}
                    onToggleShowAnnotation={(e) => {
                        e.stopPropagation();
                        onToggleShowAnnotation(annotation.sample_id);
                    }}
                    onToggleLock={(e) => {
                        e.stopPropagation();
                        toggleAnnotationLock(annotation.sample_id);
                    }}
                    onUpdate={refetch}
                    onChangeAnnotationLabel={(newLabel) => {
                        // The annotation label is always the last selected label.
                        setAnnotationLabel(newLabel);
                        updateLastAnnotationLabel(collectionId, newLabel);

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
                        setAnnotationId(annotation.sample_id);
                    }}
                />
            </div>
        {/each}
    </div>
</Segment>
