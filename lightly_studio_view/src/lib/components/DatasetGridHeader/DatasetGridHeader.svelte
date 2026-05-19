<script lang="ts">
    import { CollectionSearch, GridHeader, OrderBy } from '$lib/components';
    import GridHeaderSelectAllButton from '$lib/components/GridHeaderSelectAllButton/GridHeaderSelectAllButton.svelte';
    import { Button } from '$lib/components/ui/index.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import { ChartNetwork } from '@lucide/svelte';

    type SearchImage = { name: string; previewUrl: string };

    type Props = {
        canSelectAll: boolean;
        isImages: boolean;
        isVideos: boolean;
        hasEmbeddings: boolean;
        datasetId: string;
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
        canSelectAll,
        isImages,
        isVideos,
        hasEmbeddings,
        datasetId,
        onSelectAll,
        searchImage,
        searchPending,
        initialQueryText,
        onSubmitText,
        onSubmitFile,
        onSearchClear,
        onSearchError
    }: Props = $props();

    const { showPlot, setShowPlot } = useGlobalStorage();

    const canShowPlotToggle = $derived((isImages || isVideos) && hasEmbeddings);
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
            <OrderBy {datasetId} />
        {/if}
        {#if canShowPlotToggle}
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
