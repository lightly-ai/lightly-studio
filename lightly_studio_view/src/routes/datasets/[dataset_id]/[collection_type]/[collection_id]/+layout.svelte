<script lang="ts">
    import { browser } from '$app/environment';
    import { page } from '$app/state';
    import {
        CombinedMetadataDimensionsFilters,
        Footer,
        Header,
        LabelsMenu,
        TagsMenu,
        CollectionLayout,
        CollectionSearchBar
    } from '$lib/components';
    import { SlidersHorizontal, ChartNetwork } from '@lucide/svelte';
    import { onDestroy, onMount } from 'svelte';
    import { toStore } from 'svelte/store';
    import { toast } from 'svelte-sonner';
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
    import { useEmbedText } from '$lib/hooks/useEmbedText/useEmbedText';
    import type { GridType } from '$lib/types';
    import { useImageAnnotationCounts } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import { Button } from '$lib/components/ui/index.js';
    import { useVideoAnnotationCounts } from '$lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.js';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters.js';
    import { useVideoFrameAnnotationCounts } from '$lib/hooks/useVideoFrameAnnotationsCount/useVideoFrameAnnotationsCount.js';
    import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds.js';
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds.js';
    import { SampleType } from '$lib/api/lightly_studio_local/types.gen.js';
    import { buildImageFilter } from '$lib/utils/buildImageFilter';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import {
        buildVideoAnnotationCountsFilter,
        buildVideoFrameAnnotationCountsFilter
    } from '$lib/utils/buildAnnotationCountsFilters';
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

    let query_text = $state($textEmbedding ? $textEmbedding.queryText : '');
    let submittedQueryText = $state($textEmbedding ? $textEmbedding.queryText : '');
    let lastAppliedTextEmbeddingQuery = $state($textEmbedding ? $textEmbedding.queryText : '');

    const embedTextQuery = $derived(
        useEmbedText({
            collectionId,
            queryText: submittedQueryText,
            embeddingModelId: null
        })
    );

    async function onKeyDown(event: KeyboardEvent) {
        const input = event.currentTarget as HTMLInputElement | null;

        if (event.key === 'Enter') {
            event.preventDefault();
            const trimmedQuery = query_text.trim();
            if (!trimmedQuery) {
                clearSearch();
                input?.blur();
                return;
            }

            query_text = trimmedQuery;
            submittedQueryText = trimmedQuery;
            input?.blur();
        }

        if (event.key === 'Escape') {
            event.preventDefault();
            if (submittedQueryText) {
                query_text = submittedQueryText;
            } else {
                query_text = '';
            }
            input?.blur();
        }
    }

    const hasEmbeddingsQuery = $derived(useHasEmbeddings({ collectionId }));
    const hasEmbeddings = $derived(!!$hasEmbeddingsQuery.data);

    const { metadataValues } = $derived.by(() => useMetadataFilters(collectionId));
    const { dimensionsValues } = useDimensions(collectionIdStore);

    const annotationLabelsQuery = $derived(
        useAnnotationLabels({ collectionId: collectionId ?? '' })
    );
    const annotationLabelsData = $derived($annotationLabelsQuery?.data);
    const { showPlot, setShowPlot, filteredSampleCount, filteredAnnotationCount } =
        useGlobalStorage();

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
    const plotSelectionImageSampleIds = $derived(
        $imageFilterFromHook?.sample_filter?.sample_ids ?? []
    );
    const plotSelectionVideoSampleIds = $derived(
        $videoFilterFromHook?.sample_filter?.sample_ids ?? []
    );

    const annotationCounts = $derived.by(() => {
        if (
            isVideoFrames ||
            (isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME)
        ) {
            let videoFrameCollectionId = collectionId;
            if (isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME)
                videoFrameCollectionId = parentCollection.collectionId;
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
                    sampleIds: plotSelectionVideoSampleIds
                })
            });
        }
        return useImageAnnotationCounts({
            collectionId: datasetId,
            filter: buildImageFilter({
                dimensionsValues: $dimensionsValues,
                annotationFilter: $annotationFilterStore,
                metadataFilters,
                sampleIds: isAnnotations ? [] : plotSelectionImageSampleIds
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

    // Error handling for text embedding search
    const setError = (errorMessage: string) => {
        toast.error('Error', { description: errorMessage });
    };

    const totalAnnotations = $derived.by(() => {
        const countsData = $annotationCounts.data;
        if (!countsData) return 0;
        return countsData.reduce((sum, item) => sum + Number(item.total_count), 0);
    });

    const MAX_IMAGE_SIZE_MB = 50;
    const MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024;

    let dragOver = $state(false);
    let activeImage = $state<string | null>(null);
    let previewUrl = $state<string | null>(null);
    let isUploading = $state(false);
    let fileInput = $state<HTMLInputElement | null>(null);

    function handleDragOver(e: DragEvent) {
        e.preventDefault();
        dragOver = true;
    }

    function handleDragLeave(e: DragEvent) {
        e.preventDefault();
        dragOver = false;
    }

    async function handleDrop(e: DragEvent) {
        e.preventDefault();
        dragOver = false;
        if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type.startsWith('image/')) {
                await uploadImage(file);
            } else {
                setError('Please drop an image file.');
            }
        }
    }

    async function handlePaste(e: ClipboardEvent) {
        const clipboardData = e.clipboardData;
        if (!clipboardData) return;

        // Check clipboardData.files first (most common case)
        if (clipboardData.files && clipboardData.files.length > 0) {
            const file = clipboardData.files[0];
            if (file.type.startsWith('image/')) {
                e.preventDefault();
                await uploadImage(file);
                return;
            }
        }

        // Fallback: check clipboardData.items (screenshots, images copied from web)
        const items = clipboardData.items;
        if (items) {
            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    const file = item.getAsFile();
                    if (file) {
                        e.preventDefault();
                        await uploadImage(file);
                        return;
                    }
                }
            }
        }
    }

    async function handleFileSelect(e: Event) {
        const target = e.target as HTMLInputElement;
        if (target.files && target.files.length > 0) {
            await uploadImage(target.files[0]);
        }
        // Reset input
        target.value = '';
    }

    async function uploadImage(file: File) {
        if (file.size > MAX_IMAGE_SIZE_BYTES) {
            setError(`Image is too large. Maximum size is ${MAX_IMAGE_SIZE_MB}MB.`);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        isUploading = true;
        try {
            const currentCollectionId = page.params.collection_id;
            if (!currentCollectionId) {
                throw new Error('Collection ID is not available');
            }
            const response = await fetch(
                `/api/image_embedding/from_file/for_collection/${currentCollectionId}`,
                {
                    method: 'POST',
                    body: formData
                }
            );

            if (!response.ok) {
                throw new Error(`Error uploading image: ${response.statusText}`);
            }

            const embedding = await response.json();

            // Clear text search state
            query_text = '';
            submittedQueryText = '';
            activeImage = file.name;

            // Create preview URL for the uploaded image
            if (previewUrl) {
                URL.revokeObjectURL(previewUrl);
            }
            previewUrl = URL.createObjectURL(file);

            setTextEmbedding({
                queryText: file.name,
                embedding: embedding
            });
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to upload image';
            setError(message);
        } finally {
            isUploading = false;
        }
    }

    function clearSearch() {
        activeImage = null;
        query_text = '';
        submittedQueryText = '';
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }
        setTextEmbedding(undefined);
    }

    $effect(() => {
        const committedQuery = $textEmbedding?.queryText ?? '';
        if (committedQuery === lastAppliedTextEmbeddingQuery) {
            return;
        }

        lastAppliedTextEmbeddingQuery = committedQuery;

        if (activeImage) {
            return;
        }

        if (!committedQuery) {
            submittedQueryText = '';
            query_text = '';
            return;
        }

        submittedQueryText = committedQuery;
        query_text = committedQuery;
    });

    function triggerFileInput() {
        fileInput?.click();
    }

    // Update effect to respect activeImage
    $effect(() => {
        if (activeImage) return;

        if ($embedTextQuery.isError && $embedTextQuery.error) {
            const queryError = $embedTextQuery.error as
                | { error?: unknown; message?: string }
                | Error;
            const message = 'error' in queryError ? queryError.error : queryError.message;
            setError(String(message));
            return;
        }

        if (!submittedQueryText) {
            setTextEmbedding(undefined);
            return;
        }

        if ($embedTextQuery.isSuccess) {
            setTextEmbedding({
                queryText: submittedQueryText,
                embedding: $embedTextQuery.data
            });
        }
    });

    const showLeftSidebar = $derived(
        isSamples || isAnnotations || isVideos || isVideoFrames || isGroups
    );
</script>

<CollectionLayout
    showDetails={isSampleDetails || isAnnotationDetails || isGroupDetails || isVideoDetails}
    {showLeftSidebar}
    showWithPlot={(isSamples || isVideos) && $showPlot}
    showGridHeader={isSamples || isAnnotations || isVideos || isGroups}
    showSelectionPill={showLeftSidebar}
    selectedCount={$selectedCount}
    onClearSelection={clearSelection}
>
    {#snippet header()}
        <Header {collection} />
        <MenuDialogHost {isSamples} {isVideos} {hasEmbeddings} {collection} />
    {/snippet}

    {#snippet sidebar()}
        <div>
            <TagsMenu collection_id={collectionId} {gridType} />
        </div>
        <Segment title="Filters" icon={SlidersHorizontal}>
            <div class="space-y-2">
                <LabelsMenu
                    {annotationFilterRows}
                    onToggleAnnotationFilter={toggleAnnotationFilterSelection}
                />
                {#if isSamples || isVideos || isVideoFrames}
                    {#key collectionId}
                        <CombinedMetadataDimensionsFilters {isVideos} {isVideoFrames} />
                    {/key}
                {/if}
            </div>
        </Segment>
    {/snippet}

    {#snippet searchBar()}
        {#if (isSamples || isVideos) && hasEmbeddings}
            <CollectionSearchBar
                queryText={query_text}
                {submittedQueryText}
                {activeImage}
                {previewUrl}
                {isUploading}
                isDragOver={dragOver}
                onQueryTextInput={(value) => {
                    query_text = value;
                }}
                {onKeyDown}
                onPaste={handlePaste}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClearSearch={clearSearch}
                onFileSelect={handleFileSelect}
            />
        {/if}
    {/snippet}

    {#snippet auxControls()}
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
    {/snippet}

    {#snippet plotPanel()}
        {#await import('$lib/components/PlotPanel/PlotPanel.svelte') then { default: PlotPanel }}
            <PlotPanel />
        {/await}
    {/snippet}

    {#snippet fewShotDialogs()}
        {#if hasEmbeddings}
            {#await import('$lib/components/FewShotClassifier/CreateClassifierDialog.svelte') then { default: CreateClassifierDialog }}
                <CreateClassifierDialog />
            {/await}
            {#await import('$lib/components/FewShotClassifier/RefineClassifierDialog.svelte') then { default: RefineClassifierDialog }}
                <RefineClassifierDialog />
            {/await}
        {/if}
    {/snippet}

    {#snippet footer()}
        <Footer
            totalSamples={collection?.total_sample_count}
            filteredSamples={$filteredSampleCount}
            {totalAnnotations}
            filteredAnnotations={$filteredAnnotationCount}
        />
    {/snippet}

    {@render children()}
</CollectionLayout>
