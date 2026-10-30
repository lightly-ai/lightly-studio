<script lang="ts">
    import WorkspacePanelHeader from '../WorkspacePanelHeader/WorkspacePanelHeader.svelte';
    import SceneViewSettings from '../SceneViewSettings/SceneViewSettings.svelte';
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
            showOrthographicViews={layout.showOrthographicViews}
            pointSize={layout.pointSize}
            showNavigationHelpers={layout.showNavigationHelpers}
            showAnnotationTooltips={layout.showAnnotationTooltips}
            onToggle={layout.onToggleOrthographicProjections}
            onPointSizeChange={layout.onPointSizeChange}
            onToggleNavigationHelpers={layout.onToggleNavigationHelpers}
            onToggleAnnotationTooltips={layout.onToggleAnnotationTooltips}
        />
    {/snippet}
</WorkspacePanelHeader>
