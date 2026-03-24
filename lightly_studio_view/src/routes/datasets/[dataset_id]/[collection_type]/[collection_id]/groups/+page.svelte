<script lang="ts">
    import { GroupsGrid } from '$lib/components/GroupsGrid';
    import { useGroupsInfinite } from '$lib/hooks/useGroupsInfinite';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { page } from '$app/stores';
    import { routeHelpers } from '$lib/routes';
    import { goto } from '$app/navigation';
    import type { GroupView } from '$lib/api/lightly_studio_local';
    import { isImageView, isVideoView } from '$lib/utils';

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

    const navigateToSampleDetailsByView = (view: GroupView) => {
        if (isVideoView(view.group_preview)) {
            goto(
                routeHelpers.toVideosDetails({
                    datasetId,
                    collectionType,
                    collectionId,
                    sampleId: view.group_preview.sample_id,
                    groupId: view.sample_id
                })
            );
        } else if (isImageView(view.group_preview)) {
            goto(
                routeHelpers.toSample({
                    datasetId,
                    collectionType,
                    collectionId,
                    sampleId: view.group_preview.sample_id,
                    groupId: view.sample_id
                })
            );
        }
    };
</script>

<GroupsGrid
    {groups}
    {isLoading}
    {isEmpty}
    {hasNextPage}
    {isFetchingNextPage}
    {navigateToSampleDetailsByView}
    onLoadMore={loadMore}
/>
