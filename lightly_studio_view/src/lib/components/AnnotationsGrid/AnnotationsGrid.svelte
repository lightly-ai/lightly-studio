<script lang="ts">
    import { AnnotationsGridItem, SelectableBox, LazyTrigger } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { routeHelpers } from '$lib/routes';
    import { onMount } from 'svelte';
    import { Grid } from 'svelte-virtual';
    import { type Readable } from 'svelte/store';
    import { page } from '$app/state';
    import { useAnnotationsInfinite } from '$lib/hooks/useAnnotationsInfinite/useAnnotationsInfinite';
    import Spinner from '../Spinner/Spinner.svelte';
    import { afterNavigate, goto } from '$app/navigation';
    import SelectedAnnotations from './SelectedAnnotations/SelectedAnnotations.svelte';
    import { useScrollRestoration } from '$lib/hooks/useScrollRestoration/useScrollRestoration';
    import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
    import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
    import { AnnotationType, type AnnotationWithPayloadView } from '$lib/api/lightly_studio_local';
    import { selectRangeByAnchor } from '$lib/utils/selectRangeByAnchor';

    type AnnotationsProps = {
        collection_id: string;
        selectedAnnotationFilterIds: Readable<string[]>;
        itemWidth: number;
    };
    const { collection_id, selectedAnnotationFilterIds, itemWidth }: AnnotationsProps = $props();

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

    let viewport: HTMLElement | null = $state(null);
    let clientWidth = $state(0);
    let clientHeight = $state(0);

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
        infiniteAnnotations.subscribe((result) => {
            if (result.isSuccess && result.data.pages.length > 0) {
                setfilteredAnnotationCount(result.data.pages[0].total_count);
            }
        });
    });

    const {
        selectedSampleAnnotationCropIds: pickedAnnotationIds,
        toggleSampleAnnotationCropSelection,
        clearSelectedSampleAnnotationCrops
    } = useGlobalStorage();

    const gridGap = 16;
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

    function handleOnClick(event: MouseEvent) {
        const annotationId = (event.currentTarget as HTMLElement).dataset.annotationId!;
        const index = Number((event.currentTarget as HTMLElement).dataset.index!);

        selectionAnchorAnnotationId = selectRangeByAnchor({
            sampleIdsInOrder: annotations.map((annotation) => annotation.annotation.sample_id),
            selectedSampleIds: $pickedAnnotationIds[collection_id] ?? new Set<string>(),
            clickedSampleId: annotationId,
            clickedIndex: index,
            shiftKey: event.shiftKey,
            anchorSampleId: selectionAnchorAnnotationId,
            onSelectSample: (selectedAnnotationId) => handleToggleSelection(selectedAnnotationId)
        });
    }

    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);

    function handleOnDoubleClick(event: MouseEvent) {
        const annotationId = (event.currentTarget as HTMLElement).dataset.annotationId!;
        const sampleId = (event.currentTarget as HTMLElement).dataset.sampleId!;
        const index = (event.currentTarget as HTMLElement).dataset.index!;

        if (datasetId && collectionType) {
            goto(
                routeHelpers.toSampleWithAnnotation({
                    datasetId,
                    collectionType,
                    sampleId,
                    annotationId: annotationId,
                    collectionId: collection_id,
                    annotationIndex: Number(index)
                })
            );
        }
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            const annotationId = (event.currentTarget as HTMLElement).dataset.annotationId!;
            const index = Number((event.currentTarget as HTMLElement).dataset.index!);
            selectionAnchorAnnotationId = selectRangeByAnchor({
                sampleIdsInOrder: annotations.map((annotation) => annotation.annotation.sample_id),
                selectedSampleIds: $pickedAnnotationIds[collection_id] ?? new Set<string>(),
                clickedSampleId: annotationId,
                clickedIndex: index,
                shiftKey: event.shiftKey,
                anchorSampleId: selectionAnchorAnnotationId,
                onSelectSample: (selectedAnnotationId) =>
                    handleToggleSelection(selectedAnnotationId)
            });
        }
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

    const size = $derived.by(() => {
        if (clientWidth === 0) {
            return 0;
        }
        return clientWidth / itemWidth;
    });
    const annotationSize = $derived(Math.max(size - gridGap, 0));
    const viewportHeight = $derived(clientHeight);
</script>

{#if $infiniteAnnotations.isFetched && annotations.length === 0}
    <div class="flex h-full flex-1 items-center justify-center">
        <div class="text-center text-muted-foreground">
            <div class="mb-2 text-lg font-medium">No annotations found</div>
            <div class="text-sm">This collection doesn't contain any annotations.</div>
        </div>
    </div>
{:else}
    <div
        class="flex h-full flex-1"
        data-testid="annotations-grid"
        bind:this={viewport}
        bind:clientWidth
        bind:clientHeight
    >
        <div class="viewport flex-1">
            {#key infiniteLoaderIdentifier}
                <Grid
                    itemCount={annotations?.length}
                    itemHeight={size}
                    itemWidth={size}
                    height={viewportHeight}
                    scrollPosition={annotations.length > 0 ? initialScrollPosition : 0}
                    onscroll={handleScroll}
                    class="overflow-none overflow-y-auto dark:[color-scheme:dark]"
                    style="--sample-width: {annotationSize}px; --sample-height: {annotationSize}px;"
                >
                    {#snippet item({ index, style }: { index: number; style: string })}
                        {#key $infiniteAnnotations.dataUpdatedAt}
                            {#if annotations[index]}
                                <div
                                    class="annotation-grid-item relative select-none"
                                    {style}
                                    data-testid="annotation-grid-item"
                                    data-annotation-id={annotations[index].annotation.sample_id}
                                    data-sample-id={annotations[index].annotation.parent_sample_id}
                                    data-index={index}
                                    onclick={handleOnClick}
                                    ondblclick={handleOnDoubleClick}
                                    onkeydown={handleKeyDown}
                                    aria-label={`Edit annotation: ${annotations[index].annotation.sample_id}`}
                                    role="button"
                                    tabindex="0"
                                >
                                    <!-- Hide the SelectableBox when in editing mode -->
                                    <div class="absolute right-7 top-1 z-10">
                                        <SelectableBox
                                            onSelect={() => undefined}
                                            isSelected={$pickedAnnotationIds[collection_id]?.has(
                                                annotations[index].annotation.sample_id
                                            )}
                                        />
                                    </div>

                                    <AnnotationsGridItem
                                        annotation={annotations[index]}
                                        width={annotationSize}
                                        height={annotationSize}
                                        cachedCollectionVersion={collectionVersion}
                                        showLabel={showLabels}
                                        selected={$pickedAnnotationIds[collection_id]?.has(
                                            annotations[index].annotation.sample_id
                                        )}
                                    />
                                </div>
                            {/if}
                        {/key}
                    {/snippet}
                    {#snippet footer()}
                        {#key annotations.length}
                            <LazyTrigger onIntersect={handleLoadMore} />
                        {/key}
                        {#if $infiniteAnnotations.isFetchingNextPage}
                            <div class="flex justify-center p-4">
                                <Spinner />
                            </div>
                        {/if}
                    {/snippet}
                </Grid>
            {/key}
        </div>
        {#if $isEditingMode}
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
{/if}

<style>
    .annotation-grid-item:focus {
        outline: none;
    }

    .annotation-grid-item:focus-visible {
        outline: none;
    }
</style>
