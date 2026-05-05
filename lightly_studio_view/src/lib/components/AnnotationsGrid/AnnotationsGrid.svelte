<script lang="ts">
    import { AnnotationsGridItem, SelectableBox } from '$lib/components';
    import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { routeHelpers } from '$lib/routes';
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { useAnnotationsInfinite } from '$lib/hooks/useAnnotationsInfinite/useAnnotationsInfinite';
    import { afterNavigate, goto } from '$app/navigation';
    import SelectedAnnotations from './SelectedAnnotations/SelectedAnnotations.svelte';
    import { useScrollRestoration } from '$lib/hooks/useScrollRestoration/useScrollRestoration';
    import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
    import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
    import { AnnotationType, type AnnotationWithPayloadView } from '$lib/api/lightly_studio_local';
    import { selectRangeByAnchor } from '$lib/utils/selectRangeByAnchor';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { GridContainer } from '$lib/components/GridContainer';
    import { Grid } from '$lib/components/Grid';
    import { GridItem } from '$lib/components/GridItem';

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
        clearReversibleActions
    } = useGlobalStorage();

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
        path: {
            collection_id: collection_id
        },
        query: {
            annotation_label_ids:
                $selectedAnnotationFilterIds.length > 0 ? $selectedAnnotationFilterIds : undefined,
            tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined
        }
    });

    const {
        annotations: infiniteAnnotations,
        updateAnnotations,
        refresh,
        isPending
    } = $derived(useAnnotationsInfinite(queryParams));

    const { updateAnnotations: updateAnnotationsRaw } = useUpdateAnnotationsMutation({
        collectionId: collection_id
    });
    let infiniteLoaderIdentifier = $derived(
        $selectedAnnotationFilterIds.join(',') + Array.from($tagsSelected).join(',')
    );

    const filterHash = $derived(infiniteLoaderIdentifier);

    // Get initial scroll position (0 if filters changed, saved position if same filters).
    const initialScrollPosition = $derived(getRestoredPosition(filterHash));

    function handleScroll(event: Event) {
        const scrollTop = (event.target as HTMLElement).scrollTop;
        savePosition(scrollTop, filterHash);
    }

    $effect(() => {
        const unsubscribe = infiniteAnnotations.subscribe((result) => {
            if (result.isSuccess && result.data.pages.length > 0) {
                setfilteredAnnotationCount(result.data.pages[0].total_count);
            }
        });

        return unsubscribe;
    });

    const { user } = useAuth();
    const {
        selectedSampleAnnotationCropIds: pickedAnnotationIds,
        toggleSampleAnnotationCropSelection,
        clearSelectedSampleAnnotationCrops
    } = useGlobalStorage();

    let selectionAnchorAnnotationId = $state<string | null>(null);

    function handleToggleSelection(annotationId: string) {
        if (annotationId) {
            toggleSampleAnnotationCropSelection(collection_id, annotationId);
        }
    }

    // Skip the classification annotations
    // because we don't have support for the annotation views
    const annotations: AnnotationWithPayloadView[] = $derived(
        $infiniteAnnotations.data?.pages.flatMap((page) =>
            page.data.filter(
                (annotation) =>
                    annotation.annotation.annotation_type != AnnotationType.CLASSIFICATION
            )
        ) || []
    );

    function handleLoadMore() {
        if ($infiniteAnnotations.hasNextPage) {
            $infiniteAnnotations.fetchNextPage();
        }
    }

    function handleAnnotationSelect(annotationId: string, index: number, shiftKey: boolean) {
        selectionAnchorAnnotationId = selectRangeByAnchor({
            sampleIdsInOrder: annotations.map((annotation) => annotation.annotation.sample_id),
            selectedSampleIds: $pickedAnnotationIds[collection_id] ?? new Set<string>(),
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

    const selectedAnnotations = $derived(
        annotations
            .map((annotation) => annotation.annotation)
            .filter((annotation) => $pickedAnnotationIds[collection_id]?.has(annotation.sample_id))
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
        $infiniteAnnotations.isFetched && annotations.length === 0
    );
</script>

<div class="flex h-full flex-1">
    <div class="flex-1">
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
                loading: $infiniteAnnotations.isPending && annotations.length === 0,
                error: $infiniteAnnotations.isError && annotations.length === 0,
                empty: $infiniteAnnotations.isFetched && annotations.length === 0,
                success: annotations.length > 0
            }}
            loader={{
                loadMore: handleLoadMore,
                disabled:
                    !$infiniteAnnotations.hasNextPage || $infiniteAnnotations.isFetchingNextPage,
                loading: $infiniteAnnotations.isFetchingNextPage
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
                        {#key $infiniteAnnotations.dataUpdatedAt}
                            {#if annotations[index]}
                                <GridItem
                                    {width}
                                    {height}
                                    {style}
                                    dataTestId="annotation-grid-item"
                                    tag={false}
                                    ariaLabel={`Edit annotation: ${annotations[index].annotation.sample_id}`}
                                    onSelect={(event) =>
                                        handleGridItemSelect(
                                            event,
                                            annotations[index].annotation.sample_id,
                                            index
                                        )}
                                    ondblclick={() =>
                                        handleOnDoubleClick(
                                            annotations[index].annotation.sample_id
                                        )}
                                >
                                    <div
                                        class="annotation-grid-item relative h-full w-full"
                                        data-annotation-id={annotations[index].annotation.sample_id}
                                        data-annotation-index={index}
                                        data-sample-id={annotations[index].annotation
                                            .parent_sample_id}
                                        data-index={index}
                                    >
                                        {#if hasMinimumRole(user?.role, 'labeler') && $pickedAnnotationIds[collection_id]?.has(annotations[index].annotation.sample_id)}
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

                                        <AnnotationsGridItem
                                            annotation={annotations[index]}
                                            {width}
                                            {height}
                                            cachedCollectionVersion={collectionVersion}
                                            showLabel={showLabels}
                                            selected={$pickedAnnotationIds[collection_id]?.has(
                                                annotations[index].annotation.sample_id
                                            )}
                                        />
                                    </div>
                                </GridItem>
                            {/if}
                        {/key}
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
