<script lang="ts">
    import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
    import { Segment } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import SampleDetailsSidePanelAnnotation from '../SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte';
    import { useAnnotationCollections, useSetTargetSource, useSettings } from '$lib/hooks';
    import { NewAnnotationSourceInput } from '$lib/components/SampleDetails/NewAnnotationSourceInput';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { countVisibleSources, resolveEffectiveColorBySource } from '$lib/utils';
    import {
        groupAnnotationsBySource,
        listAllSourceGroups
    } from './SampleDetailsAnnotationSegment.helpers';
    import { useAnnotationPanelVisibility } from './useAnnotationPanelVisibility.svelte';
    import { useAnnotationRowActions } from './useAnnotationRowActions.svelte';
    import AnnotationSourceGroupList from './AnnotationSourceGroupList/AnnotationSourceGroupList.svelte';

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
    // The target source is picked in edit mode only, like the rest of the editing controls.
    const canPickTarget = $derived(canEdit && $isEditingMode);

    const { context: annotationLabelContext } = useAnnotationLabelContext();
    const rowActions = useAnnotationRowActions({
        getCollectionId: () => collectionId,
        getAnnotations: () => annotations,
        getIsPanModeEnabled: () => isPanModeEnabled,
        refetch: () => refetch()
    });

    const annotationCollectionsQuery = useAnnotationCollections(() => ({ collectionId }));
    const { enforceColoringByClassStore } = useSettings();
    const setTargetSource = useSetTargetSource(() => collectionId);
    const targetSource = $derived(annotationLabelContext.annotationSource ?? null);

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
            targetSource
        )
    );
    const isGrouped = $derived(allSourceGroups.length > 1);

    const visibility = useAnnotationPanelVisibility({
        getSampleId: () => sampleId,
        getAnnotations: () => annotationsSort,
        getAreSourcesLoaded: () => annotationSources.length > 0,
        getGroups: () => allSourceGroups,
        getLastCreatedAnnotationId: () => annotationLabelContext.lastCreatedAnnotationId,
        getHiddenIds: () => annotationsIdsToHide,
        setHiddenIds: (ids) => (annotationsIdsToHide = ids)
    });

    // Matches the details canvas: only visible sources count. The explicit class-color
    // preference still takes priority.
    const colorBySource = $derived(
        resolveEffectiveColorBySource({
            multipleSourcesVisible: countVisibleSources(annotationsSort, annotationsIdsToHide) >= 2,
            enforceColoringByClass: $enforceColoringByClassStore
        })
    );
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
            visibility.toggleAnnotation(annotation.sample_id);
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
    {#if isGrouped}
        <AnnotationSourceGroupList
            groups={allSourceGroups}
            {sampleId}
            {targetSource}
            {canPickTarget}
            onSetTarget={setTargetSource}
            {visibility}
            {colorBySource}
            row={annotationRow}
        />
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
    {#if canPickTarget}
        <div class="mt-3">
            <NewAnnotationSourceInput
                existingNames={allSourceGroups.map((group) => group.name)}
                onSubmit={(name) => setTargetSource(name, { isNew: true })}
            />
        </div>
    {/if}
</Segment>
