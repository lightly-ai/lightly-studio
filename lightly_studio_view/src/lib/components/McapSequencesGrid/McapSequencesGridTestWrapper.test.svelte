<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import McapSequencesGrid from './McapSequencesGrid.svelte';

    let {
        sequences,
        isLoading,
        isEmpty,
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
    {hasNextPage}
    {isFetchingNextPage}
    {onLoadMore}
    {onSequenceClick}
/>
