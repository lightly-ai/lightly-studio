<script lang="ts">
    import { CollectionSearchBar } from '$lib/components';
    import type { useRouteType } from '$lib/hooks/useRouteType/useRouteType';
    import type { useEmbeddingSearch } from '$lib/hooks/useEmbeddingSearch/useEmbeddingSearch';

    const {
        routeType,
        hasEmbeddings,
        search
    }: {
        routeType: ReturnType<typeof useRouteType>;
        hasEmbeddings: boolean;
        search: ReturnType<typeof useEmbeddingSearch>;
    } = $props();
</script>

{#if (routeType.isSamples || routeType.isVideos) && hasEmbeddings}
    <CollectionSearchBar
        queryText={$search.query_text}
        submittedQueryText={$search.submittedQueryText}
        activeImage={$search.activeImage}
        previewUrl={$search.previewUrl}
        isUploading={$search.isUploading}
        isDragOver={$search.dragOver}
        onQueryTextInput={(value) => {
            search.query_text.set(value);
        }}
        onKeyDown={search.handleKeyDown}
        onPaste={search.handlePaste}
        onDragOver={search.handleDragOver}
        onDragLeave={search.handleDragLeave}
        onDrop={search.handleDrop}
        onClearSearch={search.clearSearch}
        onFileSelect={search.handleFileSelect}
    />
{/if}
