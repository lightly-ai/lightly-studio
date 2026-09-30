<script lang="ts">
    import type { PageData } from './$types';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { useFeatureFlags } from '$lib/hooks';
    import PointCloudLabelingWorkspace from '$lib/components/PointCloudLabelingWorkspace/PointCloudLabelingWorkspace.svelte';
    import { getTickNumberFromHash } from './getTickNumberFromHash';

    // The backend only reports this once LIGHTLY_STUDIO_POINT_CLOUD_ENABLED is set, so
    // this one string keeps the route (and the entry point in GroupsComponentsMenu) in sync with
    // lightly_studio/api/features.py. Disabling it never affects the existing sample detail view.
    const POINT_CLOUD_RENDERING_FEATURE = 'point_cloud_rendering';
    const { data }: { data: PageData } = $props();
    const { datasetId, sampleId, sequenceId } = $derived(data);
    const { featureFlags } = useFeatureFlags();
    const isEnabled = $derived($featureFlags.includes(POINT_CLOUD_RENDERING_FEATURE));
    const tickNumber = $derived(getTickNumberFromHash(page.url.hash));

    const updateTickNumber = (nextTickNumber: number) => {
        const url = new URL(page.url);
        const hash = new URLSearchParams(url.hash.slice(1));
        hash.set('tick', String(nextTickNumber));
        url.hash = hash.toString();
        void goto(url, {
            replaceState: true,
            noScroll: true,
            keepFocus: true,
            state: page.state
        });
    };
</script>

<div class="flex h-full min-h-0 w-full flex-1" data-testid="point-cloud-labeling-route">
    {#if isEnabled}
        <PointCloudLabelingWorkspace
            {datasetId}
            {sequenceId}
            {sampleId}
            {tickNumber}
            onTickChange={updateTickNumber}
        />
    {/if}
</div>
