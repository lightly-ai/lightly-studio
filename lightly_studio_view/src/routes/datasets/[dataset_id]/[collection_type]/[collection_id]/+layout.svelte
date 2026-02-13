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
    import Input from '$lib/components/ui/input/input.svelte';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import {
        Search,
        SlidersHorizontal,
        Image as ImageIcon,
        X,
        ChartNetwork,
        GripVertical
    } from '@lucide/svelte';
    import { onDestroy, onMount } from 'svelte';
    import { get, writable } from 'svelte/store';
    import { toast } from 'svelte-sonner';
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
        isSampleDetailsWithoutIndexRoute,
        isSamplesRoute,
        isVideoFramesRoute,
        isVideosRoute,
        isGroupsRoute
    } from '$lib/routes';
    import { useEmbedText } from '$lib/hooks/useEmbedText/useEmbedText';
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
    import { SampleType } from '$lib/api/lightly_studio_local/types.gen.js';
    import type { AnnotationLabel } from '$lib/services/types.js';

    const { data, children } = $props();
    const {
        collection,
        globalStorage: {
            setTextEmbedding,
            textEmbedding,
            setLastGridType,
            selectedAnnotationFilterIds
        }
    } = $derived(data);

    const datasetId = $derived(page.params.dataset_id!);
    const collectionId = $derived(page.params.collection_id!);

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
    const isAnnotations = $derived(isAnnotationsRoute(page.route.id));
    const isSampleDetails = $derived(isSampleDetailsRoute(page.route.id));
    const isAnnotationDetails = $derived(isAnnotationDetailsRoute(page.route.id));
    const isSampleDetailsWithoutIndex = $derived(isSampleDetailsWithoutIndexRoute(page.route.id));
    const isCaptions = $derived(isCaptionsRoute(page.route.id));
    const isVideos = $derived(isVideosRoute(page.route.id));
    const isVideoFrames = $derived(isVideoFramesRoute(page.route.id));

    let gridType = $state<GridType>('samples');
    $effect(() => {
        if (isAnnotations) {
            gridType = 'annotations';
        } else if (isSamples) {
            gridType = 'samples';
        } else if (isCaptions) {
            gridType = 'captions';
        } else if (isVideoFrames) {
            gridType = 'video_frames';
        } else if (isVideos) {
            gridType = 'videos';
        }

        // Temporary hack to remember where the user was when navigating
        // TODO: also remember state of tags, labels, metadata filters etc. Possible store it in pagestate
        setLastGridType(gridType);
    });

    let query_text = $state($textEmbedding ? $textEmbedding.queryText : '');
    let submittedQueryText = $state('');

    const embedTextQuery = $derived(
        useEmbedText({
            collectionId,
            queryText: submittedQueryText,
            embeddingModelId: null
        })
    );

    async function onKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter') {
            const trimmedQuery = query_text.trim();
            submittedQueryText = trimmedQuery;
        }
    }

    const hasEmbeddingsQuery = $derived(useHasEmbeddings({ collectionId }));
    const hasEmbeddings = $derived(!!$hasEmbeddingsQuery.data);

    const { metadataValues } = $derived.by(() => useMetadataFilters(collectionId));
    const { dimensionsValues } = $derived.by(() =>
        useDimensions(collection?.parent_collection_id ?? collectionId)
    );

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

    const annotationsLabels = $derived(
        selectedAnnotationFilter.length > 0 ? selectedAnnotationFilter : undefined
    );
    const metadataFilters = $derived(
        metadataValues ? createMetadataFilters($metadataValues) : undefined
    );
    const { videoFramesBoundsValues } = useVideoFramesBounds();
    const { videoBoundsValues } = useVideoBounds();

    const annotationCounts = $derived.by(() => {
        if (
            isVideoFrames ||
            (isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME)
        ) {
            return useVideoFrameAnnotationCounts({
                collectionId: datasetId,
                filter: {
                    annotations_labels: annotationsLabels,
                    video_filter: {
                        sample_filter: {
                            metadata_filters: metadataFilters
                        },
                        ...$videoFramesBoundsValues
                    }
                }
            });
        } else if (isVideos) {
            return useVideoAnnotationCounts({
                collectionId,
                filter: {
                    video_frames_annotations_labels: annotationsLabels,
                    video_filter: {
                        sample_filter: {
                            metadata_filters: metadataFilters
                        },
                        ...$videoBoundsValues
                    }
                }
            });
        }
        return useAnnotationCounts({
            collectionId: datasetId,
            options: {
                filtered_labels: annotationsLabels,
                dimensions: $dimensionsValues
            }
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

    function clearImageSearch() {
        activeImage = null;
        query_text = '';
        submittedQueryText = '';
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }
        setTextEmbedding({
            queryText: '',
            embedding: []
        });
    }

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
        setTextEmbedding({
            queryText: query_text,
            embedding: $embedTextQuery.data || []
        });
    });

    const showLeftSidebar = $derived(
        isSamples || isAnnotations || isVideos || isVideoFrames || isGroupsRoute
    );
</script>

<div class="flex-none">
    <Header {collection} />
    <MenuDialogHost {isSamples} {isVideos} {hasEmbeddings} {collection} />
</div>

<div class="relative flex min-h-0 flex-1 flex-col">
    {#if isSampleDetails || isAnnotationDetails || isSampleDetailsWithoutIndex}
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
                                        <div
                                            class="relative"
                                            role="region"
                                            aria-label="Search by image or text"
                                            ondragover={handleDragOver}
                                            ondragleave={handleDragLeave}
                                            ondrop={handleDrop}
                                        >
                                            <Search
                                                class="absolute left-2 top-[50%] h-4 w-4 translate-y-[-50%] text-muted-foreground"
                                            />
                                            {#if activeImage}
                                                <div
                                                    class="flex h-10 w-full items-center rounded-md border border-input bg-background px-3 py-2 pl-8 text-sm {dragOver
                                                        ? 'ring-2 ring-primary'
                                                        : ''}"
                                                >
                                                    <span
                                                        class="mr-2 flex items-center gap-2 truncate text-muted-foreground"
                                                    >
                                                        {#if previewUrl}
                                                            <img
                                                                src={previewUrl}
                                                                alt="Search preview"
                                                                class="h-6 w-6 rounded object-cover"
                                                            />
                                                        {:else}
                                                            <ImageIcon class="h-4 w-4" />
                                                        {/if}
                                                        {activeImage}
                                                    </span>
                                                    <button
                                                        class="ml-auto hover:text-foreground"
                                                        onclick={clearImageSearch}
                                                        title="Clear image search"
                                                    >
                                                        <X class="h-4 w-4" />
                                                    </button>
                                                </div>
                                            {:else}
                                                <Input
                                                    placeholder={isUploading
                                                        ? 'Uploading...'
                                                        : 'Search samples by description or image'}
                                                    class="pl-8 pr-8 {dragOver
                                                        ? 'ring-2 ring-primary'
                                                        : ''}"
                                                    bind:value={query_text}
                                                    onkeydown={onKeyDown}
                                                    onpaste={handlePaste}
                                                    disabled={isUploading}
                                                    data-testid="text-embedding-search-input"
                                                />
                                                <button
                                                    class="absolute right-2 top-[50%] translate-y-[-50%] text-muted-foreground hover:text-foreground disabled:opacity-50"
                                                    onclick={triggerFileInput}
                                                    title="Upload image for search"
                                                    disabled={isUploading}
                                                >
                                                    <ImageIcon class="h-4 w-4" />
                                                </button>
                                            {/if}
                                            <input
                                                type="file"
                                                accept="image/*"
                                                class="hidden"
                                                bind:this={fileInput}
                                                onchange={handleFileSelect}
                                                disabled={isUploading}
                                            />
                                        </div>
                                    {/if}
                                </div>

                                <div class="w-4/12">
                                    <ImageSizeControl />
                                </div>
                                {#if hasEmbeddings}
                                    <Button
                                        class="flex items-center space-x-1"
                                        data-testid="toggle-plot-button"
                                        variant={$showPlot ? 'default' : 'ghost'}
                                        onclick={() => setShowPlot(!$showPlot)}
                                    >
                                        <ChartNetwork class="size-4" />
                                        <span>Hide Embeddings</span>
                                    </Button>
                                {/if}
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

                    <Pane defaultSize={50} minSize={30} class="flex flex-col">
                        <PlotPanel />
                    </Pane>
                </PaneGroup>
            {:else}
                <!-- When plot is hidden or not samples view, show normal layout -->
                <div class="flex flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4 pb-2">
                    {#if isSamples || isAnnotations || isVideos}
                        <div class="my-2 flex items-center space-x-4">
                            <div class="flex-1">
                                <!-- Conditional rendering for the search bar -->
                                {#if (isSamples || isVideos) && hasEmbeddings}
                                    <div
                                        class="relative"
                                        role="region"
                                        aria-label="Search by image or text"
                                        ondragover={handleDragOver}
                                        ondragleave={handleDragLeave}
                                        ondrop={handleDrop}
                                    >
                                        <Search
                                            class="absolute left-2 top-[50%] h-4 w-4 translate-y-[-50%] text-muted-foreground"
                                        />
                                        {#if activeImage}
                                            <div
                                                class="flex h-10 w-full items-center rounded-md border border-input bg-background px-3 py-2 pl-8 text-sm {dragOver
                                                    ? 'ring-2 ring-primary'
                                                    : ''}"
                                            >
                                                <span
                                                    class="mr-2 flex items-center gap-2 truncate text-muted-foreground"
                                                >
                                                    {#if previewUrl}
                                                        <img
                                                            src={previewUrl}
                                                            alt="Search preview"
                                                            class="h-6 w-6 rounded object-cover"
                                                        />
                                                    {:else}
                                                        <ImageIcon class="h-4 w-4" />
                                                    {/if}
                                                    {activeImage}
                                                </span>
                                                <button
                                                    class="ml-auto hover:text-foreground"
                                                    onclick={clearImageSearch}
                                                    title="Clear image search"
                                                >
                                                    <X class="h-4 w-4" />
                                                </button>
                                            </div>
                                        {:else}
                                            <Input
                                                placeholder={isUploading
                                                    ? 'Uploading...'
                                                    : 'Search samples by description or image'}
                                                class="pl-8 pr-8 {dragOver
                                                    ? 'ring-2 ring-primary'
                                                    : ''}"
                                                bind:value={query_text}
                                                onkeydown={onKeyDown}
                                                onpaste={handlePaste}
                                                disabled={isUploading}
                                                data-testid="text-embedding-search-input"
                                            />
                                            <button
                                                class="absolute right-2 top-[50%] translate-y-[-50%] text-muted-foreground hover:text-foreground disabled:opacity-50"
                                                onclick={triggerFileInput}
                                                title="Upload image for search"
                                                disabled={isUploading}
                                            >
                                                <ImageIcon class="h-4 w-4" />
                                            </button>
                                        {/if}
                                        <input
                                            type="file"
                                            accept="image/*"
                                            class="hidden"
                                            bind:this={fileInput}
                                            onchange={handleFileSelect}
                                            disabled={isUploading}
                                        />
                                    </div>
                                {/if}
                            </div>

                            <div class="w-4/12">
                                <ImageSizeControl />
                            </div>
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
