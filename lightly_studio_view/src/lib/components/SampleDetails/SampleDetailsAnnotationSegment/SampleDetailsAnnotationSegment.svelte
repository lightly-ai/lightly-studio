<script lang="ts">
    import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
    import { SampleDetailsAnnotationSourceGroup, Segment } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import SampleDetailsSidePanelAnnotation from '../SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte';
    import {
        useAnnotationCollections,
        useAnnotationCollectionsFilter,
        useSettings
    } from '$lib/hooks';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { countVisibleSources, resolveEffectiveColorBySource } from '$lib/utils';
    import {
        areAllAnnotationsHidden,
        computeSeededHiddenIds,
        groupAnnotationsBySource,
        isSourceGroupInitiallyOpen,
        toggleSourceVisibility
    } from './SampleDetailsAnnotationSegment.helpers';
    import { useAnnotationSourceGroupState } from './useAnnotationSourceGroupState';
    import { useAnnotationRowActions } from './useAnnotationRowActions.svelte';

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

    const { isEditingMode } = useGlobalStorage();
    const { user } = useAuth();
    const canEdit = $derived(hasMinimumRole(user?.role, 'labeler'));

    const { context: annotationLabelContext } = useAnnotationLabelContext();
    const rowActions = useAnnotationRowActions({
        getCollectionId: () => collectionId,
        getAnnotations: () => annotations,
        getIsPanModeEnabled: () => isPanModeEnabled,
        refetch: () => refetch()
    });

    const annotationCollectionsQuery = useAnnotationCollections(() => ({ collectionId }));
    const { isSourceVisible } = useAnnotationCollectionsFilter();
    const { enforceColoringByClassStore } = useSettings();
    const { sourceGroupStates, setSourceGroupState } = useAnnotationSourceGroupState();

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
        isSelected={annotationLabelContext.annotationId === annotation.sample_id}
        onClick={() => rowActions.toggleSelection(annotation.sample_id)}
        onDeleteAnnotation={() => rowActions.remove(annotation)}
        isHidden={annotationsIdsToHide.has(annotation.sample_id)}
        isLocked={annotationLabelContext.lockedAnnotationIds?.has(annotation.sample_id) ?? false}
        onToggleShowAnnotation={(e) => {
            e.stopPropagation();
            onToggleShowAnnotation(annotation.sample_id);
        }}
        onToggleLock={(e) => {
            e.stopPropagation();
            rowActions.toggleLock(annotation.sample_id);
        }}
        onUpdate={refetch}
        onChangeAnnotationLabel={(newLabel) => rowActions.relabel(annotation, newLabel)}
        canHighlight={annotationLabelContext.lastCreatedAnnotationId === annotation.sample_id}
        onClickSelectList={() => rowActions.select(annotation.sample_id)}
    />
{/snippet}

<Segment title="Annotations">
    {#if annotationsSort.length === 0}
        <p class="text-sm text-muted-foreground" data-testid="empty-state-message">
            {#if $isEditingMode}
                No annotations. Use the toolbar to add one.
            {:else if canEdit}
                No annotations. Click <strong>Edit annotations</strong> and use the toolbar.
            {:else}
                No annotations.
            {/if}
        </p>
    {:else if isGrouped}
        <div class="flex flex-col gap-3">
            {#each sourceGroups as group (group.id)}
                <SampleDetailsAnnotationSourceGroup
                    name={group.name}
                    count={group.annotations.length}
                    {sampleId}
                    initiallyOpen={isSourceGroupInitiallyOpen(
                        group.annotations,
                        gridHiddenIds,
                        annotationLabelContext.lastCreatedAnnotationId,
                        $sourceGroupStates[group.id]?.open
                    )}
                    showColorMarker={colorBySource}
                    allHidden={areAllAnnotationsHidden(group.annotations, annotationsIdsToHide)}
                    onToggleVisibility={(e) => {
                        e.stopPropagation();
                        onToggleSourceVisibility(group.id, group.annotations);
                    }}
                    onOpenChange={(open) => setSourceGroupState(group.id, { open })}
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
