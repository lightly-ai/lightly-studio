<script lang="ts">
    import { GroupsGrid } from '$lib/components/GroupsGrid';
    import { useGroupsInfinite } from '$lib/hooks/useGroups/useGroupsInfinite';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { page } from '$app/stores';

    const collectionId = $derived($page.params.collection_id!);

    const { data, query, loadMore, totalCount } = $derived(useGroupsInfinite(collectionId));
    const { setfilteredSampleCount } = useGlobalStorage();

    $effect(() => {
        setfilteredSampleCount($totalCount);
    });

    const groups = $derived($data);
    const isLoading = $derived($query.isPending && groups.length === 0);
    const isEmpty = $derived($query.isSuccess && groups.length === 0);
    const hasNextPage = $derived($query.hasNextPage ?? false);
    const isFetchingNextPage = $derived($query.isFetchingNextPage);
</script>

<GroupsGrid
    {collectionId}
    {groups}
    {isLoading}
    {isEmpty}
    {hasNextPage}
    {isFetchingNextPage}
    onLoadMore={loadMore}
/>
