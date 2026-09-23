<script lang="ts">
    import type { PageData } from './$types';
    import { useFeatureFlags } from '$lib/hooks';
    import PointCloudLabelingWorkspace from '$lib/components/PointCloudLabelingWorkspace/PointCloudLabelingWorkspace.svelte';

    // The backend only reports this once LIGHTLY_STUDIO_POINT_CLOUD_ENABLED is set, so
    // this one string keeps the route (and the entry point in GroupsComponentsMenu) in sync with
    // lightly_studio/api/features.py. Disabling it never affects the existing sample detail view.
    const POINT_CLOUD_RENDERING_FEATURE = 'point_cloud_rendering';
    const { data }: { data: PageData } = $props();
    const { datasetId, sampleId } = $derived(data);
    const { featureFlags } = useFeatureFlags();
    const isEnabled = $derived($featureFlags.includes(POINT_CLOUD_RENDERING_FEATURE));
    const { sequenceId } = $derived(data);
</script>

<div class="flex h-full min-h-0 w-full flex-1" data-testid="point-cloud-labeling-route">
    {#if isEnabled}
        <PointCloudLabelingWorkspace {datasetId} {sequenceId} {sampleId} />
    {/if}
</div>
