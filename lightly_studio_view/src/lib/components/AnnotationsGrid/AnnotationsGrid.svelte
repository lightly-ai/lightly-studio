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
    import {
        AnnotationType,
        SampleType,
        type AnnotationWithPayloadView
    } from '$lib/api/lightly_studio_local';

    type AnnotationsProps = {
        dataset_id: string;
        selectedAnnotationFilterIds: Readable<string[]>;
        itemWidth: number;
    };
    const { dataset_id, selectedAnnotationFilterIds, itemWidth }: AnnotationsProps = $props();

    // Use the dataset_id for tags - tags should use the specific dataset, not root
    const { tagsSelected } = $derived(
        useTags({
            dataset_id: dataset_id,
            kind: ['annotation']
        })
    );

    // Access the settings store
    const { showAnnotationTextLabelsStore } = useSettings();
    const { isEditingMode } = page.data.globalStorage;

    // Track the setting value
    let showLabels = $derived($showAnnotationTextLabelsStore);

    // Add datasetVersion state and preload it
    const {
        getDatasetVersion,
        setfilteredAnnotationCount,
        addReversibleAction,
        clearReversibleActions
    } = useGlobalStorage();

    afterNavigate(() => {
        clearReversibleActions();
    });
    let datasetVersion = $state('');

    const { initialize, savePosition, getRestoredPosition } =
        useScrollRestoration('annotations_scroll');

    onMount(async () => {
        initialize();
        datasetVersion = await getDatasetVersion(dataset_id);
    });

    let viewport: HTMLElement | null = $state(null);
    let size = $state(0);
    let annotationSize = $state(0);
    let clientWidth = $state(0);

    const queryParams = $derived({
        path: {
            dataset_id: dataset_id
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
        datasetId: dataset_id
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

    function handleToggleSelection(annotationId: string) {
        if (annotationId) {
            toggleSampleAnnotationCropSelection(annotationId);
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
        handleToggleSelection(annotationId);
    }

    function handleOnDoubleClick(event: MouseEvent) {
        const annotationId = (event.currentTarget as HTMLElement).dataset.annotationId!;
        const sampleId = (event.currentTarget as HTMLElement).dataset.sampleId!;
        const index = (event.currentTarget as HTMLElement).dataset.index!;

        goto(
            routeHelpers.toSampleWithAnnotation({
                sampleId,
                annotationId: annotationId,
                datasetId: dataset_id,
                annotationIndex: Number(index)
            })
        );
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            const annotationId = (event.currentTarget as HTMLElement).dataset.annotationId!;
            handleToggleSelection(annotationId);
        }
    }

    const selectedAnnotations = $derived(
        annotations
            .map((annotation) => annotation.annotation)
            .filter((annotation) => $pickedAnnotationIds.has(annotation.sample_id))
    );

    const handleSelectLabel = async (item: { value: string; label: string }) => {
        addAnnotationLabelChangeToUndoStack({
            annotations: selectedAnnotations.map((annotation) => annotation),
            datasetId: dataset_id,
            addReversibleAction,
            updateAnnotations: updateAnnotationsRaw,
            refresh
        });

        await updateAnnotations(
            selectedAnnotations.map((annotation) => ({
                annotation_id: annotation.sample_id,
                label_name: item.value,
                dataset_id: dataset_id
            }))
        );
        clearSelectedSampleAnnotationCrops();
    };

    let viewportHeight = $state(600);

    $effect(() => {
        if (!viewport) return;
        size = clientWidth / itemWidth;
        annotationSize = size - gridGap;
        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                viewportHeight = entry.contentRect.height;
            }
        });

        resizeObserver.observe(viewport);

        return () => {
            resizeObserver.disconnect();
        };
    });
</script>

{#if $infiniteAnnotations.isFetched && annotations.length === 0}
    <div class="flex h-full flex-1 items-center justify-center">
        <div class="text-center text-muted-foreground">
            <div class="mb-2 text-lg font-medium">No annotations found</div>
            <div class="text-sm">This dataset doesn't contain any annotations.</div>
        </div>
    </div>
{:else}
    <div
        class="flex h-full flex-1"
        data-testid="annotations-grid"
        bind:this={viewport}
        bind:clientWidth
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
                                            isSelected={$pickedAnnotationIds.has(
                                                annotations[index].annotation.sample_id
                                            )}
                                        />
                                    </div>

                                    <AnnotationsGridItem
                                        annotation={annotations[index]}
                                        width={annotationSize}
                                        height={annotationSize}
                                        cachedDatasetVersion={datasetVersion}
                                        showLabel={showLabels}
                                        selected={$pickedAnnotationIds.has(
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
                />
            </div>
        {/if}
    </div>
{/if}
