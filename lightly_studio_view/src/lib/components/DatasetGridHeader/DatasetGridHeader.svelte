<script lang="ts">
    import { CollectionSearch, GridHeader, OrderBy } from '$lib/components';
    import GridHeaderSelectAllButton from '$lib/components/GridHeaderSelectAllButton/GridHeaderSelectAllButton.svelte';
    import LowCaptionMatchFilter from '$lib/components/LowCaptionMatchFilter/LowCaptionMatchFilter.svelte';

    type SearchImage = { name: string; previewUrl: string };

    interface Props {
        collectionId: string;
        canSelectAll: boolean;
        isSelectionActive: boolean;
        isImages: boolean;
        isVideos?: boolean;
        hasMediaWithEmbeddings: boolean;
        collectionDatasetId: string;
        onSelectAll: () => Promise<void>;
        onDeselectAll: () => void;
        searchImage: SearchImage | undefined;
        searchPending: boolean;
        searchPlaceholder?: string;
        initialQueryText: string;
        onSubmitText: (text: string) => void;
        onSubmitFile: (file: File) => void | Promise<void>;
        onSearchClear: () => void;
        onSearchError: (message: string) => void;
    }

    const {
        collectionId,
        canSelectAll,
        isSelectionActive,
        isImages,
        isVideos = false,
        hasMediaWithEmbeddings,
        onSelectAll,
        onDeselectAll,
        searchImage,
        searchPending,
        searchPlaceholder,
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
        {#if isVideos}
            <LowCaptionMatchFilter />
            <OrderBy {collectionId} datasetId={collectionDatasetId} mediaType="video" />
        {:else if isImages}
            <OrderBy {collectionId} datasetId={collectionDatasetId} />
        {/if}
    {/snippet}
    {#if hasMediaWithEmbeddings}
        <div class="relative" role="region" data-grid-search-drop-target>
            <CollectionSearch
                image={searchImage}
                isPending={searchPending}
                {searchPlaceholder}
                {initialQueryText}
                {onSubmitText}
                {onSubmitFile}
                onClear={onSearchClear}
                onError={onSearchError}
            />
        </div>
    {/if}
</GridHeader>
