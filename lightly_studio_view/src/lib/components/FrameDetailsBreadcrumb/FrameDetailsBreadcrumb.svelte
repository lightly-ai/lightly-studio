<script lang="ts">
    import type { CollectionView } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import DetailsBreadcrumb from '../DetailsBreadcrumb/DetailsBreadcrumb.svelte';
    import { page } from '$app/state';
    import { useAdjacentFrames } from '$lib/hooks/useAdjacentFrames/useAdjacentFrames';

    const {
        rootCollection,
        sampleId,
        collectionId
    }: {
        rootCollection: CollectionView;
        sampleId: string;
        collectionId: string;
    } = $props();
    // Get datasetId and collectionType from URL params
    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);

    const navigateToFrames = (collectionId: string) => {
        return routeHelpers.toFrames(datasetId, collectionType, collectionId);
    };

    const { query: sampleAdjacentQuery } = $derived(
        useAdjacentFrames({
            sampleId,
            collectionId
        })
    );
</script>

<DetailsBreadcrumb
    {rootCollection}
    section="Frames"
    subsection="Frame"
    navigateTo={navigateToFrames}
    index={$sampleAdjacentQuery?.data?.current_sample_position}
    totalCount={$sampleAdjacentQuery?.data?.total_count}
/>
