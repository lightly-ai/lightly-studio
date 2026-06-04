<script lang="ts">
    import { CollectionSearch, GridHeader, OrderBy } from '$lib/components';
    import GridHeaderSelectAllButton from '$lib/components/GridHeaderSelectAllButton/GridHeaderSelectAllButton.svelte';
    import { Button } from '$lib/components/ui/index.js';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { useGlobalStorage } from '$lib/hooks';
    import { ChartNetwork, Gauge } from '@lucide/svelte';

    type SearchImage = { name: string; previewUrl: string };

    interface Props {
        compact?: boolean;
        canSelectAll: boolean;
        isSelectionActive: boolean;
        isImages: boolean;
        hasEvaluationRuns: boolean;
        hasMediaWithEmbeddings: boolean;
        collectionDatasetId: string;
        onSelectAll: () => Promise<void>;
        onDeselectAll: () => void;
        searchImage: SearchImage | undefined;
        searchPending: boolean;
        initialQueryText: string;
        onSubmitText: (text: string) => void;
        onSubmitFile: (file: File) => void | Promise<void>;
        onSearchClear: () => void;
        onSearchError: (message: string) => void;
    }

    const {
        compact = false,
        canSelectAll,
        isSelectionActive,
        isImages,
        hasEvaluationRuns,
        hasMediaWithEmbeddings,
        onSelectAll,
        onDeselectAll,
        searchImage,
        searchPending,
        initialQueryText,
        onSubmitText,
        onSubmitFile,
        onSearchClear,
        onSearchError,
        collectionDatasetId
    }: Props = $props();

    const { showEmbeddingPlot, setShowEmbeddingPlot, showEvaluationRuns, setShowEvaluationRuns } =
        useGlobalStorage();
</script>

<GridHeader>
    {#snippet selectionControls()}
        {#if canSelectAll}
            <GridHeaderSelectAllButton checked={isSelectionActive} {onSelectAll} {onDeselectAll} />
        {/if}
    {/snippet}
    {#snippet auxControls()}
        {#if isImages}
            <OrderBy datasetId={collectionDatasetId} />
        {/if}
        {#if hasMediaWithEmbeddings}
            <Tooltip
                content={$showEmbeddingPlot ? 'Hide Embeddings plot' : 'Show Embeddings plot'}
                position="bottom"
            >
                <Button
                    class="flex items-center space-x-1"
                    data-testid="toggle-plot-button"
                    variant={$showEmbeddingPlot ? 'default' : 'ghost'}
                    onclick={() => setShowEmbeddingPlot(!$showEmbeddingPlot)}
                >
                    <ChartNetwork class="size-4" />
                    {#if !compact}
                        <span>Embeddings</span>
                    {/if}
                </Button>
            </Tooltip>
        {/if}
        {#if isImages && hasEvaluationRuns}
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
                        <span>Evaluation</span>
                    {/if}
                </Button>
            </Tooltip>
        {/if}
    {/snippet}
    {#if hasMediaWithEmbeddings}
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
