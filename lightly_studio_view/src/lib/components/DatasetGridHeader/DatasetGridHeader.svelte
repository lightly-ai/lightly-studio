<script lang="ts">
    import {
        AnnotationOrderBy,
        CollectionSearch,
        GridHeader,
        ImageOrderBy,
        VideoOrderBy
    } from '$lib/components';
    import GridHeaderSelectAllButton from '$lib/components/GridHeaderSelectAllButton/GridHeaderSelectAllButton.svelte';

    type SearchImage = { name: string; previewUrl: string };

    interface Props {
        collectionId: string;
        canSelectAll: boolean;
        isSelectionActive: boolean;
        isImages: boolean;
        isVideos: boolean;
        isAnnotations: boolean;
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
        isVideos,
        isAnnotations,
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
        {#if isImages}
            <ImageOrderBy {collectionId} datasetId={collectionDatasetId} />
        {:else if isVideos}
            <VideoOrderBy {collectionId} />
        {:else if isAnnotations}
            <AnnotationOrderBy {collectionId} />
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
