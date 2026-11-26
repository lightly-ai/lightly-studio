<script lang="ts">
    import WorkspacePanelHeader from '../WorkspacePanelHeader/WorkspacePanelHeader.svelte';
    import SceneViewSettings from '../SceneViewSettings/SceneViewSettings.svelte';
    import WorkspaceSceneFilters from '../WorkspaceSceneFilters/WorkspaceSceneFilters.svelte';
    import ViewportExpandButton from '../ViewportExpandButton/ViewportExpandButton.svelte';
    import { usePointCloudWorkspaceLayoutContext } from '../pointCloudWorkspaceLayoutContext.svelte';
    import { useWorkspaceSceneLayout } from '../workspaceSceneLayoutContext.svelte';
    const getLayout = usePointCloudWorkspaceLayoutContext();
    const layout = $derived(getLayout());
    const scene = useWorkspaceSceneLayout();
</script>

<WorkspacePanelHeader title="3D scene">
    {#snippet actions()}
        {#if layout.showOrthographicViews}
            <ViewportExpandButton
                expanded={scene.expandedProjection === 'perspective'}
                label="3D scene"
                onToggle={() => scene.toggleExpanded('perspective')}
            />
        {/if}
        <SceneViewSettings
            accumulation={layout.accumulation}
            pointSize={layout.pointSize}
            showNavigationHelpers={layout.showNavigationHelpers}
            onPointSizeChange={layout.onPointSizeChange}
            onToggleNavigationHelpers={layout.onToggleNavigationHelpers}
        >
            {#snippet filters()}
                <WorkspaceSceneFilters
                    referenceFrames={layout.workspace.referenceFrames}
                    referenceFrameId={layout.workspace.referenceFrameId}
                    onSelectReferenceFrame={layout.workspace.selectReferenceFrame}
                    isShowingSensorFrames={layout.workspace.isShowingSensorFrames}
                    colorMode={layout.colorMode}
                    onColorModeChange={layout.onColorModeChange}
                    lidarChannels={layout.workspace.lidarChannels}
                    selectedLidarChannels={layout.selectedLidarChannelIds}
                    onToggleLidarChannel={layout.onToggleLidarChannel}
                    onSetLidarChannels={layout.onSetLidarChannels}
                />
            {/snippet}
        </SceneViewSettings>
    {/snippet}
</WorkspacePanelHeader>
