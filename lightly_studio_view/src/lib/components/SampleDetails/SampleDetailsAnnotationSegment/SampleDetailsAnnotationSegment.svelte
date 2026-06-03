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
    import {
        areAllAnnotationsHidden,
        computeSeededHiddenIds,
        countVisibleSources,
        groupAnnotationsBySource
    } from './SampleDetailsAnnotationSegment.helpers';

    type SampleDetailsAnnotationSegmentProps = {
        annotationsIdsToHide: Set<string>;
        collectionId: string;
        sampleId: string;
        annotations: AnnotationView[];
        isPanModeEnabled: boolean;
        refetch: () => void;
    };

    let {
        annotationsIdsToHide = $bindable<Set<string>>(new Set()),
        collectionId,
        sampleId,
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

    // Annotations are colored by source only while multiple sources are visible,
    // matching the details canvas. Swatches are shown only when they match the
    // colors drawn on the image: source markers in the group headers when coloring
    // by source, label legends in the rows otherwise.
    const colorBySource = $derived(countVisibleSources(annotationsSort, annotationsIdsToHide) >= 2);

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

    // Tracks which sample the hidden set was seeded for. Intentionally not reactive:
    // it must not re-trigger the seeding effect.
    let seededSampleId: string | undefined = undefined;

    // Seed the local visibility state from the grid's annotation source filter, once
    // per sample. Annotations of unselected sources start hidden
    // but stay re-showable locally without touching the global grid filter.
    // Refetches (same sample) keep manual changes; navigating to a sample re-seeds.
    // Waits until both the sources query and the annotations are available so an
    // empty hidden set is never locked in prematurely.
    $effect(() => {
        if (
            seededSampleId === sampleId ||
            annotationSources.length === 0 ||
            annotationsSort.length === 0
        ) {
            return;
        }

        seededSampleId = sampleId;
        annotationsIdsToHide = computeSeededHiddenIds(
            annotationsSort,
            $selectedCollectionIds,
            annotationSources
        );
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

    // Bulk-toggles the visibility of all annotations of one source. Hides them all
    // unless they are already all hidden, in which case it shows them all.
    const onToggleSourceVisibility = (groupAnnotations: AnnotationView[]) => {
        const hideAll = !areAllAnnotationsHidden(groupAnnotations, annotationsIdsToHide);
        const next = new Set(annotationsIdsToHide);
        for (const annotation of groupAnnotations) {
            if (hideAll) {
                next.add(annotation.sample_id);
            } else {
                next.delete(annotation.sample_id);
            }
        }
        annotationsIdsToHide = next;
    };
</script>

{#snippet annotationRow(annotation: AnnotationView)}
    <SampleDetailsSidePanelAnnotation
        {annotation}
        {colorBySource}
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
                    showColorMarker={colorBySource}
                    allHidden={areAllAnnotationsHidden(group.annotations, annotationsIdsToHide)}
                    onToggleVisibility={(e) => {
                        e.stopPropagation();
                        onToggleSourceVisibility(group.annotations);
                    }}
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
