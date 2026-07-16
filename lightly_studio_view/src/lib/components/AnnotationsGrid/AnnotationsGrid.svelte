<script lang="ts">
    import { AnnotationsGridItem, SelectableBox } from '$lib/components';
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
    import { afterNavigate, goto } from '$app/navigation';
    import SelectedAnnotations from './SelectedAnnotations/SelectedAnnotations.svelte';
    import { useScrollRestoration } from '$lib/hooks/useScrollRestoration/useScrollRestoration';
    import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
    import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
    import {
        AnnotationType,
        type AnnotationView,
        type AnnotationWithPayloadView
    } from '$lib/api/lightly_studio_local';
    import { selectRangeByAnchor } from '$lib/utils/selectRangeByAnchor';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { GridContainer } from '$lib/components/GridContainer';
    import { Grid } from '$lib/components/Grid';
    import { GridItem } from '$lib/components/GridItem';
    import { buildAnnotationDragData } from './AnnotationsGrid.helpers';
    import { renderCropObjectUrl, type CropWindow } from './AnnotationItem/renderCropObjectUrl';
    import AnnotationClassificationGridItem from './AnnotationClassificationGridItem/AnnotationClassificationGridItem.svelte';
    import { groupClassificationsBySample } from './groupClassificationsBySample';

    type AnnotationsProps = {
        collection_id: string;
        itemWidth: number;
    };
    const { collection_id, itemWidth }: AnnotationsProps = $props();

    const { selectedAnnotationFilterIdsArray: selectedAnnotationFilterIds } =
        useSelectedAnnotationsFilter();

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
    let cropWindowByAnnotationId = $state<Record<string, CropWindow>>({});
    let cropUrlByAnnotationId = $state<Record<string, string>>({});

    function handleCropWindowChange(annotationId: string, window: CropWindow | null) {
        if (window) {
            cropWindowByAnnotationId[annotationId] = window;
            return;
        }
        delete cropWindowByAnnotationId[annotationId];
        revokeCropUrl(annotationId);
    }

    function revokeCropUrl(annotationId: string) {
        const url = cropUrlByAnnotationId[annotationId];
        if (url) {
            URL.revokeObjectURL(url);
            delete cropUrlByAnnotationId[annotationId];
        }
    }

    async function handleAnnotationDragStart(annotationId: string) {
        const window = cropWindowByAnnotationId[annotationId];
        if (!window) return;
        revokeCropUrl(annotationId);
        const url = await renderCropObjectUrl(window, { cancelled: false });
        // The tile may have unmounted while rendering; drop the blob if so.
        if (url && cropWindowByAnnotationId[annotationId]) {
            cropUrlByAnnotationId[annotationId] = url;
        } else if (url) {
            URL.revokeObjectURL(url);
        }
    }

    onDestroy(() => {
        for (const url of Object.values(cropUrlByAnnotationId)) {
            URL.revokeObjectURL(url);
        }
    });

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
        text_embedding: searchEmbedding?.embedding ?? undefined
    });

    const {
        annotations: infiniteAnnotations,
        updateAnnotations,
        refresh,
        isPending
    } = useAnnotationsInfinite(() => queryParams);

    const { updateAnnotations: updateAnnotationsRaw } = useUpdateAnnotationsMutation({
        collectionId: collection_id
    });
    let infiniteLoaderIdentifier = $derived(
        $selectedAnnotationFilterIds.join(',') +
            Array.from($tagsSelected).join(',') +
            (plotSelectedRegion ? JSON.stringify(plotSelectedRegion) : '') +
            (searchEmbedding ? `search:${searchEmbedding.queryText}` : '')
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

    let selectionAnchorAnnotationId = $state<string | null>(null);

    function handleToggleSelection(annotationId: string) {
        if (annotationId) {
            toggleSampleAnnotationCropSelection(collection_id, annotationId);
        }
    }

    const allAnnotations: AnnotationWithPayloadView[] = $derived(
        infiniteAnnotations.data?.pages.flatMap((page) => page.data) ?? []
    );

    // Classification can return multiple annotations for the same sample; collapse them into
    // one tile before rendering so multi-label samples appear once in the grid.
    const classificationTiles = $derived(groupClassificationsBySample(allAnnotations));
    const classificationTileMap = $derived(
        new Map(classificationTiles.map((tile) => [tile.sampleId, tile]))
    );

    type ClassificationTile = ReturnType<typeof groupClassificationsBySample>[number];
    type GridDisplayItem =
        | {
              kind: 'annotation';
              data: AnnotationWithPayloadView;
              displayId: string;
              annotationId: string;
          }
        | {
              kind: 'classification';
              data: ClassificationTile;
              displayId: string;
              annotationId: string;
          };

    // The grid works with one flat list for selection and navigation. `displayId` is the
    // selection key; `annotationId` is the route target when opening sample details.
    const gridItems: GridDisplayItem[] = $derived.by(() => {
        const emittedSampleIds = new Set<string>();

        return allAnnotations.reduce<GridDisplayItem[]>((items, annotation) => {
            if (annotation.annotation.annotation_type === AnnotationType.CLASSIFICATION) {
                const sampleId = annotation.annotation.parent_sample_id;

                if (!emittedSampleIds.has(sampleId)) {
                    emittedSampleIds.add(sampleId);

                    const tile = classificationTileMap.get(sampleId);

                    if (tile) {
                        items.push({
                            kind: 'classification' as const,
                            data: tile,
                            displayId: tile.sampleId,
                            annotationId: tile.representative.annotation.sample_id
                        });
                    }
                }

                return items;
            }

            items.push({
                kind: 'annotation' as const,
                data: annotation,
                displayId: annotation.annotation.sample_id,
                annotationId: annotation.annotation.sample_id
            });

            return items;
        }, []);
    });

    function getGridItemDragData(item: GridDisplayItem) {
        if (item.kind !== 'annotation') {
            // Classification tiles aggregate a full parent sample and do not expose crop geometry.
            return undefined;
        }

        return buildAnnotationDragData(
            item.data.annotation,
            cropWindowByAnnotationId[item.annotationId],
            cropUrlByAnnotationId[item.annotationId]
        );
    }

    function handleGridItemDragStart(item: GridDisplayItem) {
        if (item.kind !== 'annotation') {
            return;
        }

        return handleAnnotationDragStart(item.annotationId);
    }

    function handleLoadMore() {
        if (infiniteAnnotations.hasNextPage) {
            infiniteAnnotations.fetchNextPage();
        }
    }

    function handleAnnotationSelect(annotationId: string, index: number, shiftKey: boolean) {
        selectionAnchorAnnotationId = selectRangeByAnchor({
            sampleIdsInOrder: gridItems.map((item) => item.displayId),
            selectedSampleIds: selectedAnnotationIds,
            clickedSampleId: annotationId,
            clickedIndex: index,
            shiftKey,
            anchorSampleId: selectionAnchorAnnotationId,
            onSelectSample: (selectedAnnotationId) => handleToggleSelection(selectedAnnotationId)
        });
    }

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

    function handleGridItemSelect(
        event: MouseEvent | KeyboardEvent,
        annotationId: string,
        index: number
    ) {
        handleAnnotationSelect(annotationId, index, event.shiftKey);
    }

    const selectedAnnotations: AnnotationView[] = $derived(
        gridItems
            .filter((item) => selectedAnnotationIds.has(item.displayId))
            .flatMap((item) =>
                item.kind === 'annotation'
                    ? [item.data.annotation]
                    : item.data.allAnnotations.map((annotation) => annotation.annotation)
            )
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
            selectedAnnotations.map((annotation) => ({
                annotation_id: annotation.sample_id,
                label_name: item.value,
                collection_id: collection_id
            }))
        );
        clearSelectedSampleAnnotationCrops(collection_id);
    };

    const scrollResetKey = $derived(infiniteLoaderIdentifier);
    const hideSelectedAnnotationsPanel = $derived(
        infiniteAnnotations.isFetched && gridItems.length === 0
    );
</script>

<div class="flex h-full min-w-0 flex-1">
    <div class="min-w-0 flex-1">
        <GridContainer
            itemCount={gridItems.length}
            message={{
                loading: 'Loading annotations...',
                error: 'Error loading annotations',
                empty: {
                    title: 'No annotations found',
                    description: "This collection doesn't contain any annotations."
                }
            }}
            status={{
                loading: infiniteAnnotations.isPending && gridItems.length === 0,
                error: infiniteAnnotations.isError && gridItems.length === 0,
                empty: infiniteAnnotations.isFetched && gridItems.length === 0,
                success: gridItems.length > 0
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
                    itemCount={gridItems.length}
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
                        {#if gridItems[index]}
                            {@const gridItem = gridItems[index]}
                            {#key gridItem.displayId}
                                <GridItem
                                    {width}
                                    {height}
                                    {style}
                                    dataTestId="annotation-grid-item"
                                    tag={false}
                                    ariaLabel={`Edit annotation: ${gridItem.annotationId}`}
                                    dragData={getGridItemDragData(gridItem)}
                                    onDragStart={() => handleGridItemDragStart(gridItem)}
                                    onSelect={(event) =>
                                        handleGridItemSelect(event, gridItem.displayId, index)}
                                    ondblclick={() => handleOnDoubleClick(gridItem.annotationId)}
                                >
                                    <div
                                        class="annotation-grid-item relative h-full w-full"
                                        data-annotation-id={gridItem.annotationId}
                                        data-annotation-index={index}
                                        data-sample-id={gridItem.displayId}
                                        data-index={index}
                                    >
                                        {#if gridItem.kind === 'annotation' && hasMinimumRole(user?.role, 'labeler') && selectedAnnotationIds.has(gridItem.displayId)}
                                            <div
                                                class="pointer-events-none absolute right-2 top-1.5 z-10"
                                                inert
                                            >
                                                <SelectableBox
                                                    onSelect={() => undefined}
                                                    isSelected={true}
                                                />
                                            </div>
                                        {/if}

                                        {#if gridItem.kind === 'annotation'}
                                            <AnnotationsGridItem
                                                annotation={gridItem.data}
                                                {width}
                                                {height}
                                                cachedCollectionVersion={collectionVersion}
                                                showLabel={showLabels}
                                                selected={selectedAnnotationIds.has(
                                                    gridItem.displayId
                                                )}
                                                onCropWindowChange={handleCropWindowChange}
                                            />
                                        {:else}
                                            <AnnotationClassificationGridItem
                                                tile={gridItem.data}
                                                containerWidth={width}
                                                containerHeight={height}
                                                selected={selectedAnnotationIds.has(
                                                    gridItem.displayId
                                                )}
                                                cachedCollectionVersion={collectionVersion}
                                            />
                                        {/if}
                                    </div>
                                </GridItem>
                            {/key}
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
                {selectedAnnotations}
                disabled={selectedAnnotations.length === 0}
                isLoading={$isPending}
                onSelect={handleSelectLabel}
                collectionId={collection_id}
            />
        </div>
    {/if}
</div>
