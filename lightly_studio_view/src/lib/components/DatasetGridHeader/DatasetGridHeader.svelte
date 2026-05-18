<script lang="ts">
    import { CollectionSearch, GridHeader, OrderBy } from '$lib/components';
    import GridHeaderSelectAllButton from '$lib/components/GridHeaderSelectAllButton/GridHeaderSelectAllButton.svelte';
    import { Button } from '$lib/components/ui/index.js';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import { ChartNetwork, Gauge } from '@lucide/svelte';

    type SearchImage = { name: string; previewUrl: string };

    type Props = {
        compact: boolean;
        canSelectAll: boolean;
        isImages: boolean;
        isVideos: boolean;
        hasEmbeddings: boolean;
        onSelectAll: () => Promise<void>;
        searchImage: SearchImage | undefined;
        searchPending: boolean;
        initialQueryText: string;
        onSubmitText: (text: string) => void;
        onSubmitFile: (file: File) => void | Promise<void>;
        onSearchClear: () => void;
        onSearchError: (message: string) => void;
    };

    const {
        compact,
        canSelectAll,
        isImages,
        isVideos,
        hasEmbeddings,
        onSelectAll,
        searchImage,
        searchPending,
        initialQueryText,
        onSubmitText,
        onSubmitFile,
        onSearchClear,
        onSearchError
    }: Props = $props();

    const { showPlot, setShowPlot, showEvaluationRuns, setShowEvaluationRuns } = useGlobalStorage();

    const canShowPlotToggle = $derived((isImages || isVideos) && hasEmbeddings);
    const canShowEvaluationRunsToggle = $derived(isImages);
    const canShowSearch = $derived((isImages || isVideos) && hasEmbeddings);
</script>

<GridHeader>
    {#snippet selectionControls()}
        {#if canSelectAll}
            <GridHeaderSelectAllButton onclick={onSelectAll} />
        {/if}
    {/snippet}
    {#snippet auxControls()}
        {#if isImages}
            <OrderBy />
        {/if}
        {#if canShowPlotToggle}
            <Tooltip
                content={$showPlot ? 'Hide Embeddings plot' : 'Show Embeddings plot'}
                position="bottom"
            >
                <Button
                    class="flex items-center space-x-1"
                    data-testid="toggle-plot-button"
                    variant={$showPlot ? 'default' : 'ghost'}
                    onclick={() => setShowPlot(!$showPlot)}
                >
                    <ChartNetwork class="size-4" />
                    {#if !compact}
                        <span>Show Embeddings</span>
                    {/if}
                </Button>
            </Tooltip>
        {/if}
        {#if canShowEvaluationRunsToggle}
            <Tooltip
                content={$showEvaluationRuns ? 'Hide Evaluation Runs' : 'Show Evaluation Runs'}
                position="bottom"
            >
                <Button
                    class="flex items-center space-x-1"
                    data-testid="toggle-evaluation-runs-button"
                    variant={$showEvaluationRuns ? 'default' : 'ghost'}
                    onclick={() => setShowEvaluationRuns(!$showEvaluationRuns)}
                >
                    <Gauge class="size-4" />
                    {#if !compact}
                        <span>Evaluation Runs</span>
                    {/if}
                </Button>
            </Tooltip>
        {/if}
    {/snippet}
    {#if canShowSearch}
        <div class="relative" role="region" data-grid-search-drop-target>
            <CollectionSearch
                image={searchImage}
                isPending={searchPending}
                {initialQueryText}
                {onSubmitText}
                {onSubmitFile}
                onClear={onSearchClear}
                onError={onSearchError}
            />
        </div>
    {/if}
</GridHeader>
