<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import GroupsGrid from './GroupsGrid.svelte';

    let {
        groups,
        isLoading,
        isEmpty,
        hasNextPage,
        isFetchingNextPage,
        onLoadMore,
        navigateToGroupDetails
    }: ComponentProps<typeof GroupsGrid> = $props();
</script>

<GroupsGrid
    {groups}
    {isLoading}
    {isEmpty}
    {hasNextPage}
    {isFetchingNextPage}
    {onLoadMore}
    {navigateToGroupDetails}
/>
