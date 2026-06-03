<script lang="ts">
    import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
    import { SampleDetailsAnnotationSourceGroup, Segment } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import SampleDetailsSidePanelAnnotation from '../SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useAnnotationCollections, useAnnotationCollectionsFilter } from '$lib/hooks';
    import { addAnnotationDeleteToUndoStack } from '$lib/services/addAnnotationDeleteToUndoStack';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { toast } from 'svelte-sonner';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotationSelection } from '$lib/hooks/useAnnotationSelection/useAnnotationSelection';
    import { groupAnnotationsBySource } from './SampleDetailsAnnotationSegment.helpers';

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

    const annotationLabels = useAnnotationLabels(() => ({ collectionId }));
    const { createAnnotation } = useCreateAnnotation({
        collectionId
    });
    const { deleteAnnotation } = useDeleteAnnotation({
        collectionId
    });
    const { selectAnnotation } = useAnnotationSelection();

    const annotationCollectionsQuery = useAnnotationCollections({ collectionId });
    const { selectedCollectionIds, setSelectedCollectionIds, setCollectionIdToName } =
        useAnnotationCollectionsFilter();

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

    const annotationSources = $derived(annotationCollectionsQuery.data ?? []);
    const isGrouped = $derived(annotationSources.length > 1);
    const sourceGroups = $derived(
        isGrouped ? groupAnnotationsBySource(annotationsSort, annotationSources) : []
    );

    // Initialize the global annotation source stores when landing directly on the
    // details page (browser refresh / deep link), so annotations are colored by
    // source.
    $effect(() => {
        if (annotationSources.length > 1 && $selectedCollectionIds.length === 0) {
            setSelectedCollectionIds(annotationSources.map((source) => source.collection_id));
            setCollectionIdToName(
                Object.fromEntries(
                    annotationSources.map((source) => [source.collection_id, source.name])
                )
            );
        }
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
        if (!annotationLabels.data) return;

        const annotation = annotations?.find((a) => a.sample_id === annotationId);
        if (!annotation) return;

        const _delete = async () => {
            try {
                addAnnotationDeleteToUndoStack({
                    annotation,
                    labels: annotationLabels.data!,
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

{#snippet annotationRow(annotation: AnnotationView)}
    <SampleDetailsSidePanelAnnotation
        {annotation}
        isSelected={annotationLabelContext.annotationId === annotation.sample_id}
        onClick={() => toggleAnnotationSelection(annotation.sample_id)}
        onDeleteAnnotation={() => handleDeleteAnnotation(annotation.sample_id)}
        isHidden={annotationsIdsToHide.has(annotation.sample_id)}
        isLocked={annotationLabelContext.lockedAnnotationIds?.has(annotation.sample_id) ?? false}
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

            if (annotationLabelContext.annotationType === AnnotationType.SEGMENTATION_MASK) {
                setAnnotationId(annotation.sample_id);
            }
        }}
        canHighlight={annotationLabelContext.lastCreatedAnnotationId === annotation.sample_id}
        onClickSelectList={() => {
            setAnnotationId(annotation.sample_id);
        }}
    />
{/snippet}

<Segment title="Annotations">
    {#if isGrouped}
        <div class="flex flex-col gap-3">
            {#each sourceGroups as group (group.id)}
                <SampleDetailsAnnotationSourceGroup
                    name={group.name}
                    count={group.annotations.length}
                    showColorMarker={$selectedCollectionIds.length > 1}
                >
                    <div class="flex flex-col gap-2">
                        {#each group.annotations as annotation (annotation.sample_id)}
                            {@render annotationRow(annotation)}
                        {/each}
                    </div>
                </SampleDetailsAnnotationSourceGroup>
            {/each}
        </div>
    {:else}
        <div class="flex flex-col gap-2">
            {#each annotationsSort as annotation (annotation.sample_id)}
                {@render annotationRow(annotation)}
            {/each}
        </div>
    {/if}
</Segment>
