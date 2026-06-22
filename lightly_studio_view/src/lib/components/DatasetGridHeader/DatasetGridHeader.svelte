<script lang="ts">
    import { CollectionSearch, GridHeader, OrderBy } from '$lib/components';
    import GridHeaderSelectAllButton from '$lib/components/GridHeaderSelectAllButton/GridHeaderSelectAllButton.svelte';

    type SearchImage = { name: string; previewUrl: string };

    interface Props {
        canSelectAll: boolean;
        isSelectionActive: boolean;
        isImages: boolean;
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
        canSelectAll,
        isSelectionActive,
        isImages,
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
</script>

<GridHeader>
    {#snippet selectionControls(compact)}
        {#if canSelectAll}
            <GridHeaderSelectAllButton
                checked={isSelectionActive}
                {onSelectAll}
                {onDeselectAll}
                {compact}
            />
        {/if}
    {/snippet}
    {#snippet auxControls()}
        {#if isImages}
            <OrderBy datasetId={collectionDatasetId} />
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
