<script lang="ts">
    import type { DatasetViewWithCount } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import DetailsBreadcrumb from '../DetailsBreadcrumb/DetailsBreadcrumb.svelte';

    const {
        rootDataset,
        frameIndex
    }: {
        rootDataset: DatasetViewWithCount;
        frameIndex?: number | null | undefined;
    } = $props();
</script>

<DetailsBreadcrumb
    {rootDataset}
    index={frameIndex}
    section="Frames"
    subsection="Frame"
    navigateTo={routeHelpers.toFrames}
/>
