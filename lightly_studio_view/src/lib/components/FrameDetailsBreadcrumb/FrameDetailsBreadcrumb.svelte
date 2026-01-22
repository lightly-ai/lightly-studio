<script lang="ts">
    import type { CollectionView } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import DetailsBreadcrumb from '../DetailsBreadcrumb/DetailsBreadcrumb.svelte';
    import { page } from '$app/state';

    const {
        rootCollection,
        frameIndex
    }: {
        rootCollection: CollectionView;
        frameIndex?: number | null | undefined;
    } = $props();
    // Get datasetId and collectionType from URL params
    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);

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
