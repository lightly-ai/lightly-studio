<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import McapSequencesGrid from './McapSequencesGrid.svelte';

    let {
        sequences,
        isLoading,
        isEmpty,
        isError,
        hasNextPage,
        isFetchingNextPage,
        onLoadMore,
        onSequenceClick
    }: ComponentProps<typeof McapSequencesGrid> = $props();
</script>

<McapSequencesGrid
    {sequences}
    {isLoading}
    {isEmpty}
    {isError}
    {hasNextPage}
    {isFetchingNextPage}
    {onLoadMore}
    {onSequenceClick}
/>
