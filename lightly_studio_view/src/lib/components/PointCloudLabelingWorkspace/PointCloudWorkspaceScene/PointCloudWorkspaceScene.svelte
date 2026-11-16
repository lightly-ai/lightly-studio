<script lang="ts">
    import WorkspaceStatusPanel from '../WorkspaceStatusPanel/WorkspaceStatusPanel.svelte';
    import WorkspaceSceneHeader from '../WorkspaceSceneHeader/WorkspaceSceneHeader.svelte';
    import WorkspaceViewport from '../WorkspaceViewport/WorkspaceViewport.svelte';
    import OrthographicProjectionStrip from '../OrthographicProjectionStrip/OrthographicProjectionStrip.svelte';
    import { usePointCloudWorkspaceLayoutContext } from '../pointCloudWorkspaceLayoutContext.svelte';
    import { provideWorkspaceSceneLayout } from '../workspaceSceneLayoutContext.svelte';
    import { provideActiveViewportContext } from '../SceneViewport/activeViewportContext';
    const getLayout = usePointCloudWorkspaceLayoutContext();
    const layout = $derived(getLayout());
    const scene = provideWorkspaceSceneLayout(getLayout);
    provideActiveViewportContext();
    const hasError = $derived(
        layout.workspace.tickDetails.isError || layout.workspace.cloudPointFrame.isError
    );
</script>

{#if !layout.sceneFrame || hasError || layout.workspace.status === 'empty'}
    <WorkspaceSceneHeader />
{/if}
<div class="flex min-h-0 flex-1 flex-col">
    {#if hasError}
        <WorkspaceStatusPanel status="error" onRetry={layout.workspace.retry} />
    {:else if layout.workspace.status === 'empty'}
        <WorkspaceStatusPanel status="empty" />
    {:else if layout.sceneFrame}
        <div
            class="relative min-h-0 flex-[3]"
            hidden={scene.expandedProjection !== null && scene.expandedProjection !== 'perspective'}
        >
            <WorkspaceViewport cameraMode="perspective" />
        </div>
        {#if layout.showOrthographicViews}
            <div class="min-h-0 flex-[2]" hidden={scene.expandedProjection === 'perspective'}>
                <OrthographicProjectionStrip />
            </div>
        {/if}
    {:else if layout.workspace.status === 'loading' || layout.workspace.tickDetails.isLoading || layout.workspace.cloudPointFrame.isLoading}
        <WorkspaceStatusPanel status="loading" />
    {:else}
        <WorkspaceStatusPanel status="empty" />
    {/if}
</div>
