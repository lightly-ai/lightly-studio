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
        onSequenceOpen
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
    {onSequenceOpen}
/>
