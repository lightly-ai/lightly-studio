<script lang="ts">
    import type { CollectionViewWithCount } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import DetailsBreadcrumb from '../DetailsBreadcrumb/DetailsBreadcrumb.svelte';
    import { page } from '$app/state';

    const {
        rootCollection,
        frameIndex
    }: {
        rootCollection: CollectionViewWithCount;
        frameIndex?: number | null | undefined;
    } = $props();
    // Get datasetId and collectionType from URL params if available, otherwise use rootCollection
    const datasetId = $derived(page.params.dataset_id ?? rootCollection.collection_id!);
    const collectionType = $derived(page.params.collection_type ?? rootCollection.sample_type);

    const navigateToFrames = (collectionId: string) => {
        return routeHelpers.toFrames(datasetId, collectionType, collectionId);
    };
</script>

<DetailsBreadcrumb
    {rootCollection}
    index={frameIndex}
    section="Frames"
    subsection="Frame"
    navigateTo={navigateToFrames}
/>
