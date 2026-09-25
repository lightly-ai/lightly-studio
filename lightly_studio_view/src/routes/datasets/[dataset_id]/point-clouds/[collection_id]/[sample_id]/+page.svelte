<script lang="ts">
    import type { PageData } from './$types';
    import { page } from '$app/state';
    import { Footer, Header } from '$lib/components';
    import MenuDialogHost from '$lib/components/Header/MenuDialogHost.svelte';
    import { useFeatureFlags } from '$lib/hooks';
    import PointCloudLabelingWorkspace from '$lib/components/PointCloudLabelingWorkspace/PointCloudLabelingWorkspace.svelte';
    import { getTickNumberFromHash } from './getTickNumberFromHash';
    import { getWorkspaceSourcePath } from './getWorkspaceSourcePath';

    // The backend only reports this once LIGHTLY_STUDIO_POINT_CLOUD_ENABLED is set, so
    // this one string keeps the route (and the entry point in GroupsComponentsMenu) in sync with
    // lightly_studio/api/features.py. Disabling it never affects the existing sample detail view.
    const POINT_CLOUD_RENDERING_FEATURE = 'point_cloud_rendering';
    const { data }: { data: PageData } = $props();
    const { datasetId, sampleId, sequenceId, collection } = $derived(data);
    const { featureFlags } = useFeatureFlags();
    const isEnabled = $derived($featureFlags.includes(POINT_CLOUD_RENDERING_FEATURE));
    const tickNumber = $derived(getTickNumberFromHash(page.url.hash));
    const sourcePath = $derived(
        getWorkspaceSourcePath({
            datasetId,
            collection,
            collectionType: data.collectionType
        })
    );
</script>

<div class="flex-none">
    <Header {collection} />
    <MenuDialogHost {collection} />
</div>

<div class="flex min-h-0 flex-1 flex-col" data-testid="point-cloud-labeling-route">
    <div class="flex min-h-0 flex-1 px-4">
        {#if isEnabled}
            <PointCloudLabelingWorkspace
                {datasetId}
                {sequenceId}
                {sampleId}
                {tickNumber}
                {sourcePath}
            />
        {/if}
    </div>
    <Footer />
</div>
