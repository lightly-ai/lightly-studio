<script lang="ts">
    import { browser } from '$app/environment';
    import { page } from '$app/state';
    import {
        CombinedMetadataDimensionsFilters,
        CollectionSearch,
        Footer,
        GridHeader,
        LabelsMenu,
        SelectionPill,
        TagsMenu
    } from '$lib/components';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { SlidersHorizontal, ChartNetwork, GripVertical } from '@lucide/svelte';
    import { onDestroy, onMount } from 'svelte';
    import { toStore } from 'svelte/store';
    import { Header } from '$lib/components';
    import MenuDialogHost from '$lib/components/Header/MenuDialogHost.svelte';

    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useHasEmbeddings } from '$lib/hooks/useHasEmbeddings/useHasEmbeddings';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import {
        isAnnotationDetailsRoute,
        isAnnotationsRoute,
        isCaptionsRoute,
        isSampleDetailsRoute,
        isSamplesRoute,
        isVideoFramesRoute,
        isVideosRoute,
        isGroupsRoute,
        isGroupDetailsRoute,
        isVideoDetailsRoute
    } from '$lib/routes';
    import type { GridType } from '$lib/types';
    import { useImageAnnotationCounts } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import { Button } from '$lib/components/ui/index.js';
    import { PaneGroup, Pane, PaneResizer } from 'paneforge';
    import { useVideoAnnotationCounts } from '$lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.js';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters.js';
    import { useVideoFrameAnnotationCounts } from '$lib/hooks/useVideoFrameAnnotationsCount/useVideoFrameAnnotationsCount.js';
    import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds.js';
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds.js';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { SampleType } from '$lib/api/lightly_studio_local/types.gen';
    import { buildImageFilter } from '$lib/utils/buildImageFilter';
    import {
        buildVideoAnnotationCountsFilter,
        buildVideoFrameAnnotationCountsFilter
    } from '$lib/utils/buildAnnotationCountsFilters';
    import EmbeddingSelectionFilterItem from '$lib/components/EmbeddingSelectionFilterItem/EmbeddingSelectionFilterItem.svelte';
    import { useSelectionSummary } from '$lib/hooks';
    const { data, children } = $props();
    const {
        collection,
        globalStorage: {
            setTextEmbedding,
            textEmbedding,
            setLastGridType,
            clearSelectedSamples,
            clearSelectedSampleAnnotationCrops
        }
    } = $derived(data);

    const datasetId = $derived(page.params.dataset_id!);
    const collectionId = $derived(page.params.collection_id!);
    const collectionIdStore = toStore(() => collectionId);

    const { selectedCount, clearSelection } = $derived(useSelectionSummary(collectionId));

    // Use hideAnnotations hook
    const { handleKeyEvent } = useHideAnnotations();

    const {
        retrieveParentCollection,
        collections,
        showPlot,
        setShowPlot,
        filteredSampleCount,
        filteredAnnotationCount
    } = useGlobalStorage();

    const parentCollection = $derived.by(() =>
        retrieveParentCollection($collections, collectionId)
    );

    // Setup event handlers for keyboard shortcuts
    onMount(() => {
        if (browser) {
            window.addEventListener('keydown', handleKeyEvent);
            window.addEventListener('keyup', handleKeyEvent);
        }
    });

    onDestroy(() => {
        if (browser) {
            window.removeEventListener('keydown', handleKeyEvent);
            window.removeEventListener('keyup', handleKeyEvent);
        }
    });

    const isSamples = $derived(isSamplesRoute(page.route.id));
    const isGroups = $derived(isGroupsRoute(page.route.id));
    const isGroupDetails = $derived(isGroupDetailsRoute(page.route.id));
    const isAnnotations = $derived(isAnnotationsRoute(page.route.id));
    const isSampleDetails = $derived(isSampleDetailsRoute(page.route.id));
    const isAnnotationDetails = $derived(isAnnotationDetailsRoute(page.route.id));
    const isCaptions = $derived(isCaptionsRoute(page.route.id));
    const isVideos = $derived(isVideosRoute(page.route.id));
    const isVideoFrames = $derived(isVideoFramesRoute(page.route.id));
    const isVideoDetails = $derived(isVideoDetailsRoute(page.route.id));

    let gridType = $state<GridType>('samples');
    let lastCollectionId: string | null = null;
    $effect(() => {
        let nextGridType: GridType | null = null;
        if (isAnnotations) {
            nextGridType = 'annotations';
        } else if (isSamples) {
            nextGridType = 'samples';
        } else if (isCaptions) {
            nextGridType = 'captions';
        } else if (isVideoFrames) {
            nextGridType = 'video_frames';
        } else if (isVideos) {
            nextGridType = 'videos';
        } else if (isGroups) {
            nextGridType = 'groups';
        }

        if (!nextGridType) {
            return;
        }

        if (lastCollectionId && lastCollectionId !== collectionId) {
            clearSelectedSamples(lastCollectionId);
            clearSelectedSampleAnnotationCrops(lastCollectionId);
        }

        gridType = nextGridType;
        lastCollectionId = collectionId;

        // Temporary hack to remember where the user was when navigating
        // TODO: also remember state of tags, labels, metadata filters etc. Possible store it in pagestate
        setLastGridType(gridType);
    });

    const hasEmbeddingsQuery = $derived(useHasEmbeddings({ collectionId }));
    const hasEmbeddings = $derived(!!$hasEmbeddingsQuery.data);

    const { metadataValues } = $derived.by(() => useMetadataFilters(collectionId));
    const { dimensionsValues } = useDimensions(collectionIdStore);

    const annotationLabelsQuery = $derived(
        useAnnotationLabels({ collectionId: collectionId ?? '' })
    );
    const annotationLabelsData = $derived($annotationLabelsQuery?.data);
    const annotationLabelsStore = toStore(() => annotationLabelsData);

    // Initialize annotation filter hook (must be before annotationCounts to avoid init-order crash)
    const {
        annotationFilter: annotationFilterStore,
        annotationFilterRows,
        toggleAnnotationFilterSelection,
        setAnnotationCounts
    } = useAnnotationsFilter({
        annotationLabels: annotationLabelsStore
    });

    const metadataFilters = $derived(
        metadataValues ? createMetadataFilters($metadataValues) : undefined
    );
    const { videoFramesBoundsValues } = useVideoFramesBounds();
    const { videoBoundsValues } = useVideoBounds();

    const { imageFilter: imageFilterFromHook } = useImageFilters();
    const { videoFilter: videoFilterFromHook } = useVideoFilters();
    const plotFilterImageSampleIds = $derived(
        $imageFilterFromHook?.sample_filter?.sample_ids ?? []
    );
    const plotFilterVideoSampleIds = $derived(
        $videoFilterFromHook?.sample_filter?.sample_ids ?? []
    );

    const annotationCounts = $derived.by(() => {
        if (
            isVideoFrames ||
            (isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME)
        ) {
            let videoFrameCollectionId = collectionId;
            if (isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME) {
                videoFrameCollectionId = parentCollection?.collectionId ?? collectionId;
            }
            return useVideoFrameAnnotationCounts({
                collectionId: videoFrameCollectionId,
                filter: buildVideoFrameAnnotationCountsFilter({
                    metadataFilters,
                    annotationFilter: $annotationFilterStore,
                    videoFramesBoundsValues: $videoFramesBoundsValues
                })
            });
        } else if (isVideos) {
            return useVideoAnnotationCounts({
                collectionId,
                filter: buildVideoAnnotationCountsFilter({
                    metadataFilters,
                    annotationFilter: $annotationFilterStore,
                    videoBoundsValues: $videoBoundsValues,
                    sampleIds: plotFilterVideoSampleIds
                })
            });
        }
        return useImageAnnotationCounts({
            collectionId: datasetId,
            filter: buildImageFilter({
                dimensionsValues: $dimensionsValues,
                annotationFilter: $annotationFilterStore,
                metadataFilters,
                sampleIds: isAnnotations ? [] : plotFilterImageSampleIds
            })
        });
    });

    // Feed annotation counts back into the hook for UI-ready filter rows.
    // Only update when data is present to avoid flicker during query refetch.
    $effect(() => {
        const countsData = $annotationCounts.data;
        if (countsData) {
            setAnnotationCounts(
                countsData as { label_name: string; total_count: number; current_count?: number }[]
            );
        }
    });

    const totalAnnotations = $derived.by(() => {
        const countsData = $annotationCounts.data;
        if (!countsData) return 0;
        return countsData.reduce((sum, item) => sum + Number(item.total_count), 0);
    });

    const showLeftSidebar = $derived(
        isSamples || isAnnotations || isVideos || isVideoFrames || isGroups
    );
</script>

<div class="flex-none">
    <Header {collection} />
    <MenuDialogHost {isSamples} {isVideos} {hasEmbeddings} {collection} />
</div>

<div class="relative flex min-h-0 flex-1 flex-col">
    {#if isSampleDetails || isAnnotationDetails || isGroupDetails || isVideoDetails}
        {@render children()}
    {:else}
        <div class="flex min-h-0 flex-1 space-x-4 px-4">
            {#if showLeftSidebar}
                <div class="flex h-full min-h-0 w-80 flex-col">
                    <div class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card py-4">
                        <div
                            class="min-h-0 flex-1 space-y-2 overflow-y-auto px-4 pb-2 dark:[color-scheme:dark]"
                        >
                            <div>
                                <TagsMenu collection_id={collectionId} {gridType} />
                            </div>
                            <Segment title="Filters" icon={SlidersHorizontal}>
                                <div class="space-y-2">
                                    <EmbeddingSelectionFilterItem
                                        {collectionIdStore}
                                        {isVideos}
                                        {isSamples}
                                    />
                                    <LabelsMenu
                                        {annotationFilterRows}
                                        onToggleAnnotationFilter={toggleAnnotationFilterSelection}
                                    />

                                    {#if isSamples || isVideos || isVideoFrames}
                                        {#key collectionId}
                                            <CombinedMetadataDimensionsFilters
                                                {isVideos}
                                                {isVideoFrames}
                                            />
                                        {/key}
                                    {/if}
                                </div>
                            </Segment>
                        </div>
                    </div>
                </div>
            {/if}

            {#if (isSamples || isVideos) && $showPlot}
                <!-- When plot is shown, use PaneGroup for the main content + plot -->
                <PaneGroup direction="horizontal" class="flex-1">
                    <Pane defaultSize={50} minSize={30} class="flex">
                        <div
                            class="relative flex flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4"
                        >
                            <GridHeader>
                                <div class="flex-1">
                                    {#if hasEmbeddings}
                                        <CollectionSearch
                                            {collectionId}
                                            textEmbedding={$textEmbedding}
                                            {setTextEmbedding}
                                        />
                                    {/if}
                                </div>
                            </GridHeader>
                            <Separator class="mb-4 bg-border-hard" />
                            <div class="flex min-h-0 flex-1 overflow-hidden">
                                {@render children()}
                            </div>
                            <SelectionPill
                                selectedCount={$selectedCount}
                                onClear={clearSelection}
                            />
                        </div>
                    </Pane>

                    <PaneResizer
                        class="relative mx-2 flex w-1 cursor-col-resize items-center justify-center"
                    >
                        <div class="bg-brand z-10 flex h-7 min-w-5 items-center justify-center">
                            <GripVertical class="text-diffuse-foreground" />
                        </div>
                    </PaneResizer>

                    <Pane defaultSize={50} minSize={30} class="flex min-h-0 flex-col">
                        {#await import('$lib/components/PlotPanel/PlotPanel.svelte') then { default: PlotPanel }}
                            <PlotPanel />
                        {/await}
                    </Pane>
                </PaneGroup>
            {:else}
                <!-- When plot is hidden or not samples view, show normal layout -->
                <div class="relative flex flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4 pb-2">
                    {#if isSamples || isAnnotations || isVideos || isGroups}
                        <GridHeader>
                            {#snippet auxControls()}
                                {#if (isSamples || isVideos) && hasEmbeddings}
                                    <Button
                                        class="flex items-center space-x-1"
                                        data-testid="toggle-plot-button"
                                        variant={$showPlot ? 'default' : 'ghost'}
                                        onclick={() =>
                                            $showPlot ? setShowPlot(false) : setShowPlot(true)}
                                    >
                                        <ChartNetwork class="size-4" />
                                        <span>Show Embeddings</span>
                                    </Button>
                                {/if}
                            {/snippet}
                            {#if (isSamples || isVideos) && hasEmbeddings}
                                <CollectionSearch
                                    {collectionId}
                                    textEmbedding={$textEmbedding}
                                    {setTextEmbedding}
                                />
                            {/if}
                        </GridHeader>
                        <Separator class="mb-4 bg-border-hard" />
                    {/if}

                    <div class="flex min-h-0 flex-1">
                        {@render children()}
                    </div>
                    {#if showLeftSidebar}
                        <SelectionPill selectedCount={$selectedCount} onClear={clearSelection} />
                    {/if}
                </div>
            {/if}
            {#if hasEmbeddings}
                {#await import('$lib/components/FewShotClassifier/CreateClassifierDialog.svelte') then { default: CreateClassifierDialog }}
                    <CreateClassifierDialog />
                {/await}
                {#await import('$lib/components/FewShotClassifier/RefineClassifierDialog.svelte') then { default: RefineClassifierDialog }}
                    <RefineClassifierDialog />
                {/await}
            {/if}
        </div>
        <Footer
            totalSamples={collection?.total_sample_count}
            filteredSamples={$filteredSampleCount}
            {totalAnnotations}
            filteredAnnotations={$filteredAnnotationCount}
        />
    {/if}
</div>
