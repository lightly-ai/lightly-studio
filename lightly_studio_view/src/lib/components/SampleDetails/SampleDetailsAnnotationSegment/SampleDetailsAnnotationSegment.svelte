<script lang="ts">
    import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
    import { SampleDetailsAnnotationSourceGroup, Segment } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import SampleDetailsSidePanelAnnotation from '../SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import {
        useAnnotationCollections,
        useAnnotationCollectionsFilter,
        useMoveAnnotationsToSource,
        useSettings
    } from '$lib/hooks';
    import AnnotationSourceDropZone from '../AnnotationSourceDropZone/AnnotationSourceDropZone.svelte';
    import AnnotationTargetButton from '../AnnotationTargetButton/AnnotationTargetButton.svelte';
    import NewAnnotationSourceInput from '../NewAnnotationSourceInput/NewAnnotationSourceInput.svelte';
    import { useAnnotationTarget } from '$lib/hooks/useAnnotationTarget/useAnnotationTarget.svelte';
    import { addAnnotationDeleteToUndoStack } from '$lib/services/addAnnotationDeleteToUndoStack';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { toast } from 'svelte-sonner';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotationSelection } from '$lib/hooks/useAnnotationSelection/useAnnotationSelection';
    import { countVisibleSources, resolveEffectiveColorBySource } from '$lib/utils';
    import {
        areAllAnnotationsHidden,
        computeSeededHiddenIds,
        getTargetSourceHint,
        groupAnnotationsBySource,
        listAllSourceGroups,
        isSourceGroupInitiallyOpen,
        toggleSourceVisibility
    } from './SampleDetailsAnnotationSegment.helpers';
    import { useAnnotationSourceGroupState } from './useAnnotationSourceGroupState';
    import {
        findDropSource,
        getSourceDropMove,
        type DraggedAnnotation
    } from './annotationSourceDrop';

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

    const { addReversibleAction, updateLastAnnotationLabel, isEditingMode } = useGlobalStorage();
    const { user } = useAuth();
    const canEdit = $derived(hasMinimumRole(user?.role, 'labeler'));

    const {
        context: annotationLabelContext,
        setAnnotationId,
        setAnnotationLabel,
        setLastCreatedAnnotationId,
        setLockedAnnotationIds
    } = useAnnotationLabelContext();

    const annotationLabels = useAnnotationLabels(() => ({ collectionId }));
    const { createAnnotation } = useCreateAnnotation({ getCollectionId: () => collectionId });
    const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId: () => collectionId });
    const { selectAnnotation } = useAnnotationSelection();

    const annotationCollectionsQuery = useAnnotationCollections(() => ({ collectionId }));
    const { isSourceVisible } = useAnnotationCollectionsFilter();
    const { enforceColoringByClassStore } = useSettings();
    const { sourceGroupStates, setSourceGroupState } = useAnnotationSourceGroupState();
    const { moveToSource } = useMoveAnnotationsToSource();
    const annotationTarget = useAnnotationTarget(() => collectionId);

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
    // Every source gets a group, also without annotations here, so any source can be the target.
    const allSourceGroups = $derived(
        listAllSourceGroups(
            groupAnnotationsBySource(annotationsSort, annotationSources),
            annotationSources,
            annotationTarget.targetSource
        )
    );
    const isGrouped = $derived(allSourceGroups.length > 1);
    const sourceGroups = $derived(isGrouped ? allSourceGroups : []);
    const targetGroup = $derived(
        sourceGroups.find((group) => group.name === annotationTarget.targetSource)
    );
    const targetHint = $derived(
        getTargetSourceHint({
            targetSource: annotationTarget.targetSource,
            isTargetHidden:
                targetGroup !== undefined &&
                areAllAnnotationsHidden(targetGroup.annotations, annotationsIdsToHide)
        })
    );

    // The annotation row that is being dragged to another source, if any.
    let draggedAnnotation = $state<DraggedAnnotation | null>(null);
    const canDropOn = (sourceId: string) =>
        getSourceDropMove(draggedAnnotation, findDropSource(annotationSources, sourceId)) !== null;

    const dropDraggedAnnotationOn = async (sourceId: string) => {
        const move = getSourceDropMove(
            draggedAnnotation,
            findDropSource(annotationSources, sourceId)
        );
        draggedAnnotation = null;
        if (!move) return;
        if (await moveToSource({ collectionId, ...move })) refetch();
    };

    // Hidden set implied by the grid filter, as a derived so it's readable at mount (unlike
    // the effect-written `annotationsIdsToHide`); drives the initial collapse.
    const gridHiddenIds = $derived(computeSeededHiddenIds(annotationsSort, $isSourceVisible));
    // The seed also applies the source visibility the user set on earlier samples.
    const seededHiddenIds = $derived(
        computeSeededHiddenIds(annotationsSort, (sourceId) => {
            const hidden = $sourceGroupStates[sourceId]?.hidden;
            return hidden === undefined ? $isSourceVisible(sourceId) : !hidden;
        })
    );

    // Keep source markers and row layout stable when annotations are hidden, matching
    // the details canvas. The explicit class-color preference still takes priority.
    const colorBySource = $derived(
        resolveEffectiveColorBySource({
            multipleSourcesVisible: countVisibleSources(annotationsSort) >= 2,
            enforceColoringByClass: $enforceColoringByClassStore
        })
    );

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
        const nextHiddenIds = new Set(seededHiddenIds);
        // Keep the annotation the user just drew visible, also when its source is hidden.
        nextHiddenIds.delete(annotationLabelContext.lastCreatedAnnotationId ?? '');
        annotationsIdsToHide = nextHiddenIds;
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
                    sources: annotationSources,
                    addReversibleAction,
                    createAnnotation,
                    refetch
                });

                await deleteAnnotation(annotationId, annotation.annotation_type);
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
        const group = sourceGroups.find((sourceGroup) =>
            sourceGroup.annotations.some((annotation) => annotation.sample_id === annotationId)
        );
        if (group) rememberSourceVisibility(group.id, group.annotations);
    };

    const onToggleSourceVisibility = (sourceId: string, sourceAnnotations: AnnotationView[]) => {
        annotationsIdsToHide = toggleSourceVisibility(sourceAnnotations, annotationsIdsToHide);
        rememberSourceVisibility(sourceId, sourceAnnotations);
    };

    const rememberSourceVisibility = (sourceId: string, sourceAnnotations: AnnotationView[]) => {
        setSourceGroupState(sourceId, {
            hidden: areAllAnnotationsHidden(sourceAnnotations, annotationsIdsToHide)
        });
    };
</script>

{#snippet annotationRow(annotation: AnnotationView)}
    <SampleDetailsSidePanelAnnotation
        {annotation}
        {colorBySource}
        onDragStart={isGrouped
            ? () =>
                  (draggedAnnotation = {
                      annotationId: annotation.sample_id,
                      sourceId: annotation.annotation_collection_id
                  })
            : undefined}
        onDragEnd={() => (draggedAnnotation = null)}
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
            selectAnnotation({
                annotationId: annotation.sample_id,
                annotations,
                collectionId
            });
        }}
    />
{/snippet}

<Segment title="Annotations">
    {#if isGrouped}
        <div class="flex flex-col gap-3">
            {#if targetHint && canEdit}
                <p class="text-xs text-amber-400" data-testid="annotation-target-hint">
                    {targetHint}
                </p>
            {/if}
            {#each sourceGroups as group (group.id)}
                {@const isTarget = group.name === annotationTarget.targetSource}
                <AnnotationSourceDropZone
                    canDrop={canDropOn(group.id)}
                    sourceName={group.name}
                    onDrop={() => dropDraggedAnnotationOn(group.id)}
                >
                    <SampleDetailsAnnotationSourceGroup
                        name={group.name}
                        count={group.annotations.length}
                        {sampleId}
                        initiallyOpen={group.annotations.length > 0 &&
                            isSourceGroupInitiallyOpen(
                                group.annotations,
                                gridHiddenIds,
                                annotationLabelContext.lastCreatedAnnotationId,
                                $sourceGroupStates[group.id]?.open
                            )}
                        showColorMarker={colorBySource}
                        highlighted={isTarget && canEdit}
                        allHidden={areAllAnnotationsHidden(group.annotations, annotationsIdsToHide)}
                        onToggleVisibility={group.annotations.length > 0
                            ? (e) => {
                                  e.stopPropagation();
                                  onToggleSourceVisibility(group.id, group.annotations);
                              }
                            : undefined}
                        onOpenChange={(open) => setSourceGroupState(group.id, { open })}
                    >
                        {#snippet leading()}
                            {#if canEdit}
                                <AnnotationTargetButton
                                    sourceName={group.name}
                                    {isTarget}
                                    needsPick={annotationTarget.targetSource === null}
                                    onSetTarget={() => annotationTarget.setTargetSource(group.name)}
                                />
                            {/if}
                        {/snippet}
                        {#if group.annotations.length === 0}
                            <p class="text-sm text-muted-foreground">
                                No annotations on this sample.
                            </p>
                        {:else}
                            <div class="flex flex-col gap-2">
                                {#each group.annotations as annotation (annotation.sample_id)}
                                    {@render annotationRow(annotation)}
                                {/each}
                            </div>
                        {/if}
                    </SampleDetailsAnnotationSourceGroup>
                </AnnotationSourceDropZone>
            {/each}
        </div>
    {:else if annotationsSort.length === 0}
        <p class="text-sm text-muted-foreground" data-testid="empty-state-message">
            {#if $isEditingMode}
                No annotations. Use the toolbar to add one.
            {:else if canEdit}
                No annotations. Click <strong>Edit annotations</strong> and use the toolbar.
            {:else}
                No annotations.
            {/if}
        </p>
    {:else}
        <div class="flex flex-col gap-2">
            {#each annotationsSort as annotation (annotation.sample_id)}
                {@render annotationRow(annotation)}
            {/each}
        </div>
    {/if}
    {#if canEdit}
        <div class="mt-3">
            <NewAnnotationSourceInput
                existingNames={allSourceGroups.map((group) => group.name)}
                onSubmit={annotationTarget.setTargetSource}
            />
        </div>
    {/if}
</Segment>
