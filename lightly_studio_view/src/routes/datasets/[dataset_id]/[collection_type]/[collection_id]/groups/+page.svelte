<script lang="ts">
    import { GroupsGrid } from '$lib/components/GroupsGrid';
    import { useGroupsInfinite } from '$lib/hooks/useGroupsInfinite';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { page } from '$app/stores';
    import { routeHelpers } from '$lib/routes';
    import { goto } from '$app/navigation';

    const collectionId = $derived($page.params.collection_id!);
    const collectionType = $derived($page.params.collection_type!);
    const datasetId = $derived($page.params.dataset_id!);

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

    const navigateToGroupDetails = (groupId: string) => {
        goto(routeHelpers.toGroupDetails(datasetId, collectionType, collectionId, groupId));
    };
</script>

<GroupsGrid
    {groups}
    {isLoading}
    {isEmpty}
    {hasNextPage}
    {isFetchingNextPage}
    {navigateToGroupDetails}
    onLoadMore={loadMore}
/>
