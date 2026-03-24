<script lang="ts">
    import { browser } from '$app/environment';
    import { page } from '$app/state';
    import {
        CreateClassifierDialog,
        CombinedMetadataDimensionsFilters,
        Footer,
        ImageSizeControl,
        LabelsMenu,
        RefineClassifierDialog,
        TagCreateDialog,
        TagsMenu
    } from '$lib/components';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { SlidersHorizontal, ChartNetwork, GripVertical } from '@lucide/svelte';
    import { onDestroy, onMount } from 'svelte';
    import { get, toStore, writable } from 'svelte/store';
    import { Header } from '$lib/components';
    import MenuDialogHost from '$lib/components/Header/MenuDialogHost.svelte';

    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useHasEmbeddings } from '$lib/hooks/useHasEmbeddings/useHasEmbeddings';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
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
        isGroupComponentDetailsRoute
    } from '$lib/routes';
    import type { GridType } from '$lib/types';
    import { useAnnotationCounts } from '$lib/hooks/useAnnotationCounts/useAnnotationCounts';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import PlotPanel from '$lib/components/PlotPanel/PlotPanel.svelte';
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
    import {
        SampleType,
        type AnnotationsFilter,
        type ImageFilter
    } from '$lib/api/lightly_studio_local/types.gen.js';
    import type { AnnotationLabel } from '$lib/services/types.js';
    import { buildImageFilter } from '$lib/utils/buildImageFilter';
    import {
        buildVideoAnnotationCountsFilter,
        buildVideoFrameAnnotationCountsFilter
    } from '$lib/utils/buildAnnotationCountsFilters';
    import GridSearch from '$lib/components/GridSearch/GridSearch.svelte';
    const { data, children } = $props();
    const {
        collection,
        globalStorage: {
            textEmbedding,
            setLastGridType,
            clearSelectedSamples,
            clearSelectedSampleAnnotationCrops,
            selectedAnnotationFilterIds
        }
    } = $derived(data);

    const datasetId = $derived(page.params.dataset_id!);
    const collectionId = $derived(page.params.collection_id!);
    const collectionIdStore = toStore(() => collectionId);

    // Use hideAnnotations hook
    const { handleKeyEvent } = useHideAnnotations();

    const { retrieveParentCollection, collections } = useGlobalStorage();

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
    const isGroupComponentDetails = $derived(isGroupComponentDetailsRoute(page.route.id));
    const isAnnotations = $derived(isAnnotationsRoute(page.route.id));
    const isSampleDetails = $derived(isSampleDetailsRoute(page.route.id));
    const isAnnotationDetails = $derived(isAnnotationDetailsRoute(page.route.id));
    const isCaptions = $derived(isCaptionsRoute(page.route.id));
    const isVideos = $derived(isVideosRoute(page.route.id));
    const isVideoFrames = $derived(isVideoFramesRoute(page.route.id));

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

    const annotationLabels = $derived(useAnnotationLabels({ collectionId: collectionId ?? '' }));
    const { showPlot, setShowPlot, filteredSampleCount, filteredAnnotationCount } =
        useGlobalStorage();

    // Create annotation filter labels mapping (name -> id)
    const annotationFilterLabels = $derived.by(() =>
        $annotationLabels?.data
            ? $annotationLabels.data.reduce(
                  (acc: Record<string, string>, label: AnnotationLabel) => ({
                      ...acc,
                      [label.annotation_label_name!]: label.annotation_label_id!
                  }),
                  {} as Record<string, string>
              )
            : {}
    );

    const selectedAnnotationFilter = $derived.by(() => {
        const labelsMap = annotationFilterLabels;
        const currentSelectedIds = Array.from($selectedAnnotationFilterIds);

        return Object.entries(labelsMap)
            .filter(([, id]) => currentSelectedIds.includes(id))
            .map(([name]) => name);
    });

    // Helper function to add selection state to annotation counts
    const getAnnotationFilters = (annotations: Array<AnnotationCount>, selected: string[]) =>
        annotations.map((annotation) => ({
            ...annotation,
            selected: selected.includes(annotation.label_name)
        }));

    const annotationFilter = $derived.by<AnnotationsFilter | undefined>(() =>
        $selectedAnnotationFilterIds.size > 0
            ? { annotation_label_ids: Array.from($selectedAnnotationFilterIds) }
            : undefined
    );
    const metadataFilters = $derived(
        metadataValues ? createMetadataFilters($metadataValues) : undefined
    );
    const imageFilter = $derived.by<ImageFilter | undefined>(() =>
        buildImageFilter({
            dimensionsValues: $dimensionsValues ?? undefined,
            annotationFilter,
            metadataFilters,
            collectionId: collectionId
        })
    );
    const { videoFramesBoundsValues } = useVideoFramesBounds();
    const { videoBoundsValues } = useVideoBounds();

    const annotationCounts = $derived.by(() => {
        if (
            isVideoFrames ||
            (isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME)
        ) {
            let videoFrameCollectionId = collectionId;
            // If we are on the video frame annotations page we must pass the parent collectionId as annotations
            // collection is a child of video frame collection.
            if (isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME)
                videoFrameCollectionId = parentCollection.collectionId;
            return useVideoFrameAnnotationCounts({
                collectionId: videoFrameCollectionId,
                filter: buildVideoFrameAnnotationCountsFilter({
                    metadataFilters,
                    annotationFilter,
                    videoFramesBoundsValues: $videoFramesBoundsValues
                })
            });
        } else if (isVideos) {
            return useVideoAnnotationCounts({
                collectionId,
                filter: buildVideoAnnotationCountsFilter({
                    metadataFilters,
                    annotationFilter,
                    videoBoundsValues: $videoBoundsValues
                })
            });
        }
        return useAnnotationCounts({
            collectionId: datasetId,
            filter: imageFilter
        });
    });

    type AnnotationCount = {
        label_name: string;
        total_count: number;
        current_count?: number;
    };

    // Create a writable store for annotation filters that the component can subscribe to
    const annotationFilters = writable<
        Array<{
            label_name: string;
            total_count: number;
            current_count?: number;
            selected: boolean;
        }>
    >([]);

    // Use effect to update the writable store when query data or selection changes
    $effect(() => {
        const countsData = $annotationCounts.data;
        if (countsData) {
            const filtersWithSelection = getAnnotationFilters(
                countsData as AnnotationCount[],
                selectedAnnotationFilter
            );
            annotationFilters.set(filtersWithSelection);
        }
    });

    const toggleAnnotationFilterSelection = (labelName: string) => {
        // Get the ID for this label
        const labelId = annotationFilterLabels[labelName];

        if (labelId) {
            // Update the global Set in useGlobalStorage
            selectedAnnotationFilterIds.update((state: Set<string>) => {
                if (state.has(labelId)) {
                    state.delete(labelId);
                } else {
                    state.add(labelId);
                }
                return state;
            });
        }
    };

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
    {#if isSampleDetails || isAnnotationDetails || isGroupDetails || isGroupComponentDetails}
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
                                <TagCreateDialog
                                    {collectionId}
                                    {gridType}
                                    {selectedAnnotationFilterIds}
                                    textEmbedding={get(textEmbedding)}
                                />
                            </div>
                            <Segment title="Filters" icon={SlidersHorizontal}>
                                <div class="space-y-2">
                                    <LabelsMenu
                                        {annotationFilters}
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
                        <div class="flex flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4">
                            <div class="my-2 flex items-center space-x-4">
                                <div class="flex-1">
                                    {#if hasEmbeddings}
                                        <GridSearch />
                                    {/if}
                                </div>

                                <ImageSizeControl />
                            </div>
                            <Separator class="mb-4 bg-border-hard" />
                            <div class="flex min-h-0 flex-1 overflow-hidden">
                                {@render children()}
                            </div>
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
                        <PlotPanel />
                    </Pane>
                </PaneGroup>
            {:else}
                <!-- When plot is hidden or not samples view, show normal layout -->
                <div class="flex flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4 pb-2">
                    {#if isSamples || isAnnotations || isVideos || isGroups}
                        <div class="my-2 flex items-center space-x-4">
                            <div class="flex-1">
                                <!-- Conditional rendering for the search bar -->
                                {#if (isSamples || isVideos) && hasEmbeddings}
                                    <GridSearch />
                                {/if}
                            </div>

                            <ImageSizeControl />
                            {#if (isSamples || isVideos) && hasEmbeddings}
                                <Button
                                    class="flex items-center space-x-1"
                                    data-testid="toggle-plot-button"
                                    variant={$showPlot ? 'default' : 'ghost'}
                                    onclick={() => setShowPlot(!$showPlot)}
                                >
                                    <ChartNetwork class="size-4" />
                                    <span>Show Embeddings</span>
                                </Button>
                            {/if}
                        </div>
                        <Separator class="mb-4 bg-border-hard" />
                    {/if}

                    <div class="flex min-h-0 flex-1">
                        {@render children()}
                    </div>
                </div>
            {/if}
            {#if hasEmbeddings}
                <CreateClassifierDialog />
                <RefineClassifierDialog />
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
