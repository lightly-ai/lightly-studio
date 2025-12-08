<script lang="ts">
    import type { DatasetViewWithCount } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import DetailsBreadcrumb from '../DetailsBreadcrumb/DetailsBreadcrumb.svelte';

    const {
        dataset,
        frameIndex
    }: {
        dataset: DatasetViewWithCount;
        frameIndex?: number | null | undefined;
    } = $props();
</script>

<DetailsBreadcrumb
    {dataset}
    index={frameIndex}
    section="Frames"
    subsection="Frame"
    navigateTo={routeHelpers.toFrames}
/>
