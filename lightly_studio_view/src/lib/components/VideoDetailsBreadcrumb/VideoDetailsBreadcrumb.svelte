<script lang="ts">
    import type { CollectionView } from '$lib/api/lightly_studio_local';
    import { useAdjacentVideos } from '$lib/hooks/useAdjacentVideos/useAdjacentVideos';
    import { routeHelpers } from '$lib/routes';
    import DetailsBreadcrumb from '../DetailsBreadcrumb/DetailsBreadcrumb.svelte';

    const {
        rootCollection,
        collectionType,
        datasetId,
        sampleId
    }: {
        rootCollection: CollectionView;
        collectionType: string;
        datasetId: string;
        sampleId: string;
    } = $props();

    const { query: sampleAdjacentQuery } = $derived(
        useAdjacentVideos({
            sampleId
        })
    );
</script>

<DetailsBreadcrumb
    {rootCollection}
    section="Videos"
    subsection="Video"
    navigateTo={(collectionId) =>
        datasetId && collectionType
            ? routeHelpers.toVideos(datasetId, collectionType, collectionId)
            : '#'}
    index={$sampleAdjacentQuery?.data?.current_sample_position}
    totalCount={$sampleAdjacentQuery?.data?.total_count}
/>
