<script lang="ts">
    import { CollectionSearch, GridHeader, OrderBy } from '$lib/components';
    import GridHeaderSelectAllButton from '$lib/components/GridHeaderSelectAllButton/GridHeaderSelectAllButton.svelte';
    import { Button } from '$lib/components/ui/index.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import { ChartNetwork } from '@lucide/svelte';

    type SearchImage = { name: string; previewUrl: string };

    interface Props {
        canSelectAll: boolean;
        isImages: boolean;
        hasMediaWithEmbeddings: boolean;
        datasetId: string;
        onSelectAll: () => Promise<void>;
        searchImage: SearchImage | undefined;
        searchPending: boolean;
        initialQueryText: string;
        onSubmitText: (text: string) => void;
        onSubmitFile: (file: File) => void | Promise<void>;
        onSearchClear: () => void;
        onSearchError: (message: string) => void;
    }

    const {
        canSelectAll,
        isImages,
        hasMediaWithEmbeddings,
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
        {#if hasMediaWithEmbeddings}
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
