<script lang="ts">
    import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useHasEmbeddings } from '$lib/hooks/useHasEmbeddings/useHasEmbeddings';
    import { useAnnotationPlotSelection } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { routeHelpers } from '$lib/routes';
    import { onDestroy, onMount } from 'svelte';
    import { page } from '$app/state';
    import { useAnnotationsInfinite } from '$lib/hooks/useAnnotationsInfinite/useAnnotationsInfinite';
    import { useAnnotationSortBy } from '$lib/hooks';
    import { afterNavigate, goto } from '$app/navigation';
    import SelectedAnnotations from './SelectedAnnotations/SelectedAnnotations.svelte';
    import { useScrollRestoration } from '$lib/hooks/useScrollRestoration/useScrollRestoration';
    import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
    import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
    import { useBulkDeleteAnnotations } from '$lib/hooks/useBulkDeleteAnnotations/useBulkDeleteAnnotations';
    import type { AnnotationWithPayloadView } from '$lib/api/lightly_studio_local';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { GridContainer } from '$lib/components/GridContainer';
    import { Grid } from '$lib/components/Grid';
    import { useAnnotationCropPreview } from './useAnnotationCropPreview/useAnnotationCropPreview.svelte';
    import { useAnnotationTileSelection } from './useAnnotationTileSelection/useAnnotationTileSelection';
    import AnnotationTile from './AnnotationTile/AnnotationTile.svelte';

    type AnnotationsProps = {
        collection_id: string;
        itemWidth: number;
    };
    const { collection_id, itemWidth }: AnnotationsProps = $props();

    const { selectedAnnotationFilterIdsArray: selectedAnnotationFilterIds } =
        useSelectedAnnotationsFilter();

    const { sortByFor } = useAnnotationSortBy();

    // Use the collection_id for tags - tags should use the specific collection, not root
    const { tagsSelected } = $derived(
        useTags({
            collection_id: collection_id,
            kind: ['annotation']
        })
    );

    // Access the settings store
    const { showAnnotationTextLabelsStore } = useSettings();
    const { isEditingMode } = page.data.globalStorage;

    // Track the setting value
    let showLabels = $derived($showAnnotationTextLabelsStore);

    // Add collectionVersion state and preload it
    const {
        getCollectionVersion,
        setfilteredAnnotationCount,
        addReversibleAction,
        clearReversibleActions,
        textEmbedding
    } = useGlobalStorage();

    // The embedding plot lasso selection on the annotations route, kept as geometry and sent
    // to the backend instead of a resolved sample-id list (see LIG-9903).
    const { annotationPlotRegion } = useAnnotationPlotSelection();
    const plotSelectedRegion = $derived($annotationPlotRegion);

    // The text embedding search is shared with the images tab and persists across the tab switch.
    // Only apply it when this annotation collection actually has embeddings.
    const hasEmbeddingsQuery = useHasEmbeddings(() => ({ collectionId: collection_id }));
    const searchEmbedding = $derived(hasEmbeddingsQuery.data ? $textEmbedding : undefined);

    // Drag-to-search crop preview. Tiles report only their crop geometry; the blob is
    // rendered lazily when a drag starts (not per visible tile), and revoked on unmount.
    const {
        cropWindowByAnnotationId,
        cropUrlByAnnotationId,
        handleCropWindowChange,
        handleAnnotationDragStart,
        cleanup: cleanupCropPreview
    } = useAnnotationCropPreview();

    onDestroy(cleanupCropPreview);

    afterNavigate(() => {
        clearReversibleActions();
    });
    let collectionVersion = $state('');

    const { initialize, savePosition, getRestoredPosition } =
        useScrollRestoration('annotations_scroll');

    onMount(async () => {
        initialize();
        collectionVersion = await getCollectionVersion(collection_id);
    });

    const queryParams = $derived({
        collection_id: collection_id,
        annotation_label_ids:
            $selectedAnnotationFilterIds.length > 0 ? $selectedAnnotationFilterIds : undefined,
        tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
        // Embedding plot lasso selection narrows the grid to annotations inside the region.
        embedding_region: plotSelectedRegion ?? undefined,
        // Embedding text search reorders the grid by similarity (shared with images tab).
        text_embedding: searchEmbedding?.embedding ?? undefined,
        // Similarity ordering keeps precedence, so the two are never sent together.
        sort_by: searchEmbedding ? undefined : ($sortByFor(collection_id) ?? undefined)
    });

    const {
        annotations: infiniteAnnotations,
        updateAnnotations,
        refresh,
        isPending
    } = useAnnotationsInfinite(() => queryParams);

    const { updateAnnotations: updateAnnotationsRaw } = useUpdateAnnotationsMutation({
        getCollectionId: () => collection_id
    });
    let infiniteLoaderIdentifier = $derived(
        $selectedAnnotationFilterIds.join(',') +
            Array.from($tagsSelected).join(',') +
            (plotSelectedRegion ? JSON.stringify(plotSelectedRegion) : '') +
            (searchEmbedding ? `search:${searchEmbedding.queryText}` : '') +
            (queryParams.sort_by ? `sort:${JSON.stringify(queryParams.sort_by)}` : '')
    );

    const filterHash = $derived(infiniteLoaderIdentifier);

    // Get initial scroll position (0 if filters changed, saved position if same filters).
    const initialScrollPosition = $derived(getRestoredPosition(filterHash));

    function handleScroll(event: Event) {
        const scrollTop = (event.target as HTMLElement).scrollTop;
        savePosition(scrollTop, filterHash);
    }

    $effect(() => {
        if (infiniteAnnotations.isSuccess && infiniteAnnotations.data.pages.length > 0) {
            setfilteredAnnotationCount(infiniteAnnotations.data.pages[0].total_count);
        }
    });

    const { user } = useAuth();
    const {
        selectedSampleAnnotationCropIds: pickedAnnotationIds,
        toggleSampleAnnotationCropSelection,
        clearSelectedSampleAnnotationCrops
    } = useGlobalStorage();
    const selectedAnnotationIds = $derived(
        $pickedAnnotationIds[collection_id] ?? new Set<string>()
    );

    const annotations: AnnotationWithPayloadView[] = $derived(
        infiniteAnnotations.data?.pages.flatMap((page) => page.data) ?? []
    );

    function handleLoadMore() {
        if (infiniteAnnotations.hasNextPage) {
            infiniteAnnotations.fetchNextPage();
        }
    }

    const { handleGridItemSelect } = useAnnotationTileSelection({
        getCollectionId: () => collection_id,
        getAnnotations: () => annotations,
        pickedAnnotationIds,
        toggleSelection: toggleSampleAnnotationCropSelection
    });

    const canShowSelectionOverlay = $derived(hasMinimumRole(user?.role, 'labeler'));

    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);

    function handleOnDoubleClick(annotationId: string) {
        if (datasetId && collectionType) {
            goto(
                routeHelpers.toSampleWithAnnotation({
                    datasetId,
                    collectionType,
                    annotationId: annotationId,
                    collectionId: collection_id
                })
            );
        }
    }

    const selectedAnnotations = $derived(
        annotations
            .map((annotation) => annotation.annotation)
            .filter((annotation) => selectedAnnotationIds.has(annotation.sample_id))
    );

    const handleSelectLabel = async (item: { value: string; label: string }) => {
        addAnnotationLabelChangeToUndoStack({
            annotations: selectedAnnotations.map((annotation) => annotation),
            collectionId: collection_id,
            addReversibleAction,
            updateAnnotations: updateAnnotationsRaw,
            refresh
        });

        await updateAnnotations(
            [...selectedAnnotationIds].map((annotationId) => ({
                annotation_id: annotationId,
                label_name: item.value,
                collection_id: collection_id
            }))
        );
        clearSelectedSampleAnnotationCrops(collection_id);
    };

    const { deleteAnnotations } = useBulkDeleteAnnotations();
    let isDeletingSelectedAnnotations = $state(false);

    const handleDeleteSelectedAnnotations = async () => {
        if (selectedAnnotationIds.size === 0 || isDeletingSelectedAnnotations) return;
        isDeletingSelectedAnnotations = true;
        try {
            const result = await deleteAnnotations({
                collectionId: collection_id,
                annotationIds: [...selectedAnnotationIds]
            });
            if (!result.staleSelection) {
                clearSelectedSampleAnnotationCrops(collection_id);
                refresh();
            }
        } finally {
            isDeletingSelectedAnnotations = false;
        }
    };

    const scrollResetKey = $derived(infiniteLoaderIdentifier);
    const hideSelectedAnnotationsPanel = $derived(
        infiniteAnnotations.isFetched && annotations.length === 0
    );
</script>

<div class="flex h-full min-w-0 flex-1">
    <div class="min-w-0 flex-1">
        <GridContainer
            itemCount={annotations.length}
            message={{
                loading: 'Loading annotations...',
                error: 'Error loading annotations',
                empty: {
                    title: 'No annotations found',
                    description: "This collection doesn't contain any annotations."
                }
            }}
            status={{
                loading: infiniteAnnotations.isPending && annotations.length === 0,
                error: infiniteAnnotations.isError && annotations.length === 0,
                empty: infiniteAnnotations.isFetched && annotations.length === 0,
                success: annotations.length > 0
            }}
            loader={{
                loadMore: handleLoadMore,
                disabled:
                    !infiniteAnnotations.hasNextPage || infiniteAnnotations.isFetchingNextPage,
                loading: infiniteAnnotations.isFetchingNextPage
            }}
        >
            {#snippet children({ footer })}
                <Grid
                    itemCount={annotations.length}
                    columnCount={itemWidth}
                    onScroll={handleScroll}
                    {initialScrollPosition}
                    {scrollResetKey}
                    gridProps={{
                        'data-testid': 'annotations-grid',
                        class: 'annotations-grid-scroll dark:[color-scheme:dark]'
                    }}
                >
                    {#snippet gridItem({ index, style, width, height })}
                        {#if annotations[index]}
                            {@const ann = annotations[index]}
                            <AnnotationTile
                                annotation={ann}
                                {index}
                                {width}
                                {height}
                                {style}
                                selected={$pickedAnnotationIds[collection_id]?.has(
                                    ann.annotation.sample_id
                                ) ?? false}
                                showLabel={showLabels}
                                cachedCollectionVersion={collectionVersion}
                                {canShowSelectionOverlay}
                                cropWindow={cropWindowByAnnotationId[ann.annotation.sample_id]}
                                cropUrl={cropUrlByAnnotationId[ann.annotation.sample_id]}
                                onCropWindowChange={handleCropWindowChange}
                                onDragStart={handleAnnotationDragStart}
                                onSelect={handleGridItemSelect}
                                onDoubleClick={handleOnDoubleClick}
                            />
                        {/if}
                    {/snippet}
                    {#snippet footerItem()}
                        {@render footer()}
                    {/snippet}
                </Grid>
            {/snippet}
        </GridContainer>
    </div>
    {#if $isEditingMode && !hideSelectedAnnotationsPanel}
        <div class="min-w-[250px] max-w-[30%] flex-1">
            <SelectedAnnotations
                selectedCount={selectedAnnotationIds.size}
                disabled={selectedAnnotationIds.size === 0}
                isLoading={$isPending || isDeletingSelectedAnnotations}
                onSelect={handleSelectLabel}
                onDelete={handleDeleteSelectedAnnotations}
                collectionId={collection_id}
            />
        </div>
    {/if}
</div>
