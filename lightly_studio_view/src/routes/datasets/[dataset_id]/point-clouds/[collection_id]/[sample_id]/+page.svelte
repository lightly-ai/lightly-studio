<script lang="ts">
    import type { PageData } from './$types';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import { useFeatureFlags } from '$lib/hooks';
    import { page } from '$app/state';
    import WorkspaceStatusPanel from '$lib/components/PointCloudLabelingWorkspace/WorkspaceStatusPanel/WorkspaceStatusPanel.svelte';
    import type { WorkspaceCrumb } from '$lib/components/PointCloudLabelingWorkspace/types';

    // The backend only reports this once LIGHTLY_STUDIO_POINT_CLOUD_ENABLED is set, so
    // this one string keeps the route (and the entry point in GroupsComponentsMenu) in sync with
    // lightly_studio/api/features.py. Disabling it never affects the existing sample detail view.
    const POINT_CLOUD_RENDERING_FEATURE = 'point_cloud_rendering';

    const { data }: { data: PageData } = $props();
    const { datasetId, collectionType, collectionId, sampleId, groupId } = $derived(data);

    const { featureFlags, ready } = useFeatureFlags();
    const isEnabled = $derived($featureFlags.includes(POINT_CLOUD_RENDERING_FEATURE));

    let flagsReady = $state(false);
    void ready.then(() => {
        flagsReady = true;
    });

    const sourcePath = $derived.by<WorkspaceCrumb[]>(() => {
        const collectionName = page.data.collection?.name;
        return [
            { label: 'Home', href: routeHelpers.toHome() },
            ...(collectionName
                ? [
                      {
                          label: collectionName,
                          href: routeHelpers.toCollectionHome(
                              datasetId,
                              collectionType ?? 'mcap',
                              collectionId
                          )
                      }
                  ]
                : []),
            { label: sampleId }
        ];
    });

    const handleExit = () => {
        void goto(
            groupId && collectionType
                ? routeHelpers.toGroupDetails(datasetId, collectionType, collectionId, groupId)
                : routeHelpers.toPointClouds(datasetId, collectionId)
        );
    };

    // The workspace itself (and, later, its Three.js scene) is imported dynamically so its bundle
    // is only fetched once someone actually opens the workspace, never from this route's chunk.
    const loadWorkspace = () =>
        import('$lib/components/PointCloudLabelingWorkspace/PointCloudLabelingWorkspace.svelte');

    let workspaceModule = $state(loadWorkspace());
    const retryLoadWorkspace = () => {
        workspaceModule = loadWorkspace();
    };
</script>

<div class="flex h-full min-h-0 w-full flex-1" data-testid="point-cloud-labeling-route">
    {#if !flagsReady}
        <WorkspaceStatusPanel status="loading" />
    {:else if !isEnabled}
        <WorkspaceStatusPanel status="unsupported" onExit={handleExit} />
    {:else}
        {#await workspaceModule}
            <WorkspaceStatusPanel status="loading" />
        {:then module}
            {@const Workspace = module.default}
            <!-- showProviderDiagnostics is temporary: it surfaces what the MCAP frame
                 provider reads until the 3D scene lands. See ProviderDiagnostics. -->
            <Workspace {sampleId} {sourcePath} onExit={handleExit} showProviderDiagnostics />
        {:catch}
            <WorkspaceStatusPanel status="error" onRetry={retryLoadWorkspace} onExit={handleExit} />
        {/await}
    {/if}
</div>
