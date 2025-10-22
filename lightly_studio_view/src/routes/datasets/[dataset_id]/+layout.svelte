<script lang="ts">
    import { browser } from '$app/environment';
    import { page } from '$app/state';
    import { ChartNetwork } from '@lucide/svelte';
    import {
        CreateClassifierPannel,
        CombinedMetadataDimensionsFilters,
        ImageSizeControl,
        LabelsMenu,
        RefineClassifierPannel,
        TagCreateDialog,
        TagsMenu
    } from '$lib/components';
    import Input from '$lib/components/ui/input/input.svelte';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { Search, SlidersHorizontal } from '@lucide/svelte';
    import { onDestroy, onMount } from 'svelte';
    import { derived, get, writable } from 'svelte/store';
    import { toast } from 'svelte-sonner';
    import { Header } from '$lib/components';

    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useFeatureFlags } from '$lib/hooks/useFeatureFlags/useFeatureFlags';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import {
        isAnnotationDetailsRoute,
        isAnnotationsRoute,
        isCaptionsRoute,
        isClassifiersRoute,
        isSampleDetailsRoute,
        isSampleDetailsWithoutIndexRoute,
        isSamplesRoute
    } from '$lib/routes';
    import { embedText } from '$lib/services/embedText';
    import type { GridType } from '$lib/types';
    import { useAnnotationCounts } from '$lib/hooks/useAnnotationCounts/useAnnotationCounts';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import PlotPanel from '$lib/components/PlotPanel/PlotPanel.svelte';
    import { Button } from '$lib/components/ui/index.js';
    import { PaneGroup, Pane, PaneResizer } from 'paneforge';

    const { data, children } = $props();
    const {
        datasetId,
        globalStorage: {
            setTextEmbedding,
            textEmbedding,
            setLastGridType,
            selectedAnnotationFilterIds
        }
    } = data;

    // Use hideAnnotations hook
    const { handleKeyEvent } = useHideAnnotations();

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
    const isAnnotations = $derived(isAnnotationsRoute(page.route.id));
    const isSampleDetails = $derived(isSampleDetailsRoute(page.route.id));
    const isAnnotationDetails = $derived(isAnnotationDetailsRoute(page.route.id));
    const isSampleDetailsWithoutIndex = $derived(isSampleDetailsWithoutIndexRoute(page.route.id));
    const isClassifiers = $derived(isClassifiersRoute(page.route.id));
    const isCaptions = $derived(isCaptionsRoute(page.route.id));

    let gridType = $state<GridType>('samples');
    $effect(() => {
        if (isAnnotations) {
            gridType = 'annotations';
        } else if (isClassifiers) {
            gridType = 'classifiers';
        } else if (isSamples) {
            gridType = 'samples';
        } else if (isCaptions) {
            gridType = 'captions';
        }

        // Temporary hack to remember where the user was when navigating
        // TODO: also remember state of tags, labels, metadata filters etc. Possible store it in pagestate
        setLastGridType(gridType);
    });

    let query_text = $state($textEmbedding ? $textEmbedding.queryText : '');

    async function handleTextEmbeddingSearch() {
        if (query_text.trim() === '') {
            return;
        }

        try {
            const response = await embedText({ query_text, model_id: undefined });

            return response.data;
        } catch (error) {
            setError((error as unknown as Error).message);
            console.error('Error during API call:', error);
        }
    }

    async function onKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter') {
            const textEmbedding = await handleTextEmbeddingSearch();

            setTextEmbedding({
                queryText: query_text,
                embedding: textEmbedding || []
            });
        }
    }

    const { featureFlags } = useFeatureFlags();

    const hasEmbeddingSearch = $derived.by(() => {
        return $featureFlags.some((flag) => flag === 'embeddingSearchEnabled');
    });
    const isFSCEnabled = $derived.by(() => {
        return $featureFlags.some((flag) => flag === 'fewShotClassifierEnabled');
    });

    const { dimensionsValues } = useDimensions(datasetId);

    const annotationLabels = useAnnotationLabels();
    const { showPlot, setShowPlot } = useGlobalStorage();

    // Create annotation filter labels mapping (name -> id)
    const annotationFilterLabels = derived(annotationLabels, ($labels) => {
        if (!$labels.data) return {};

        return $labels.data.reduce(
            (acc: Record<string, string>, label) => ({
                ...acc,
                [label.annotation_label_name!]: label.annotation_label_id!
            }),
            {} as Record<string, string>
        );
    });

    const selectedAnnotationFilter = $derived.by(() => {
        const labelsMap = $annotationFilterLabels;
        const currentSelectedIds = Array.from($selectedAnnotationFilterIds);

        return Object.entries(labelsMap)
            .filter(([, id]) => currentSelectedIds.includes(id))
            .map(([name]) => name);
    });

    // Helper function to add selection state to annotation counts
    const getAnnotationFilters = (
        annotations: Array<{ label_name: string; total_count: number; current_count?: number }>,
        selected: string[]
    ) =>
        annotations.map((annotation) => ({
            ...annotation,
            selected: selected.includes(annotation.label_name)
        }));

    const annotationCounts = $derived(
        useAnnotationCounts({
            datasetId,
            options: {
                filtered_labels:
                    selectedAnnotationFilter.length > 0 ? selectedAnnotationFilter : undefined,
                dimensions: $dimensionsValues
            }
        })
    );

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
            const filtersWithSelection = getAnnotationFilters(countsData, selectedAnnotationFilter);
            annotationFilters.set(filtersWithSelection);
        }
    });

    const toggleAnnotationFilterSelection = (labelName: string) => {
        // Get the ID for this label
        const labelId = get(annotationFilterLabels)[labelName];

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
</script>

<div class="flex-none">
    <Header {datasetId} />
</div>
<div class="relative min-h-0 flex-1">
    {#if isSampleDetails || isAnnotationDetails || isSampleDetailsWithoutIndex}
        {@render children()}
    {:else}
        <div class="flex h-full w-full space-x-4 px-4 pb-4">
            {#if isSamples || isAnnotations}
                <div class="flex w-80 flex-col space-y-6 rounded-[1vw] bg-card py-4">
                    <div
                        class="min-h-0 flex-1 space-y-2 overflow-y-auto px-4 dark:[color-scheme:dark]"
                    >
                        <div>
                            <TagsMenu dataset_id={datasetId} {gridType} />
                            <TagCreateDialog {datasetId} {gridType} />
                        </div>
                        <div class="space-y-1 pt-2">
                            <Button
                                asChild
                                variant="ghost"
                                size="sm"
                                class="w-full justify-start text-white underline underline-offset-2 hover:text-white"
                            >
                                <a href="https://www.lightly.ai/contact">Upgrade / Contact</a>
                            </Button>
                            <Button
                                asChild
                                variant="ghost"
                                size="sm"
                                class="w-full justify-start text-white underline underline-offset-2 hover:text-white"
                            >
                                <a href="https://docs.lightly.ai/studio/" target="_blank" rel="noreferrer">
                                    View Docs
                                </a>
                            </Button>
                        </div>
                        <Segment title="Filters" icon={SlidersHorizontal}>
                            <div class="space-y-2">
                                <LabelsMenu
                                    {annotationFilters}
                                    onToggleAnnotationFilter={toggleAnnotationFilterSelection}
                                />
                                {#if isSamples}
                                    <CombinedMetadataDimensionsFilters />
                                {/if}
                            </div>
                        </Segment>
                    </div>
                </div>
            {/if}

            {#if isSamples && $showPlot}
                <!-- When plot is shown, use PaneGroup for the main content + plot -->
                <PaneGroup direction="horizontal" class="flex-1">
                    <Pane defaultSize={50} minSize={30} class="flex">
                        <div class="flex flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4">
                            <div class="my-2 flex items-center space-x-4">
                                <div class="flex-1">
                                    {#if hasEmbeddingSearch}
                                        <div class="relative">
                                            <Search
                                                class="absolute left-2 top-[50%] h-4 w-4 translate-y-[-50%] text-muted-foreground"
                                            />
                                            <Input
                                                placeholder="Search images by description"
                                                class="pl-8"
                                                bind:value={query_text}
                                                onkeydown={onKeyDown}
                                                data-testid="text-embedding-search-input"
                                            />
                                        </div>
                                    {/if}
                                </div>

                                <div class="w-4/12">
                                    <ImageSizeControl />
                                </div>
                                {#if hasEmbeddingSearch}
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
                        class="mx-2 w-1 cursor-col-resize bg-border transition-colors hover:bg-accent"
                    />

                    <Pane defaultSize={50} minSize={30} class="flex flex-col">
                        <PlotPanel />
                    </Pane>
                </PaneGroup>
            {:else}
                <!-- When plot is hidden or not samples view, show normal layout -->
                <div class="flex flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4">
                    {#if isSamples || isAnnotations}
                        <div class="my-2 flex items-center space-x-4">
                            <div class="flex-1">
                                <!-- Conditional rendering for the search bar -->
                                {#if isSamples && hasEmbeddingSearch}
                                    <div class="relative">
                                        <Search
                                            class="absolute left-2 top-[50%] h-4 w-4 translate-y-[-50%] text-muted-foreground"
                                        />
                                        <Input
                                            placeholder="Search images by description"
                                            class="pl-8"
                                            bind:value={query_text}
                                            onkeydown={onKeyDown}
                                            data-testid="text-embedding-search-input"
                                        />
                                    </div>
                                {/if}
                            </div>

                            <div class="w-4/12">
                                <ImageSizeControl />
                            </div>
                            {#if isSamples && hasEmbeddingSearch}
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
            {#if isClassifiers && hasEmbeddingSearch && isFSCEnabled}
                <CreateClassifierPannel />
                <RefineClassifierPannel />
            {/if}
        </div>
    {/if}
</div>
