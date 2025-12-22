<script lang="ts">
    import type { CollectionViewWithCount } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import DetailsBreadcrumb from '../DetailsBreadcrumb/DetailsBreadcrumb.svelte';

    const {
        rootCollection,
        frameIndex
    }: {
        rootCollection: CollectionViewWithCount;
        frameIndex?: number | null | undefined;
    } = $props();
</script>

<DetailsBreadcrumb
    {rootCollection}
    index={frameIndex}
    section="Frames"
    subsection="Frame"
    navigateTo={routeHelpers.toFrames}
/>
