<script lang="ts">
    import type { CameraMode } from '../domain';
    import SceneViewport from '../SceneViewport/SceneViewport.svelte';
    import ToolRail from '../ToolRail/ToolRail.svelte';
    import WorkspaceSceneHeader from '../WorkspaceSceneHeader/WorkspaceSceneHeader.svelte';
    import ViewportExpandButton from '../ViewportExpandButton/ViewportExpandButton.svelte';
    import { usePointCloudWorkspaceLayoutContext } from '../pointCloudWorkspaceLayoutContext.svelte';
    import { useWorkspaceSceneLayout } from '../workspaceSceneLayoutContext.svelte';
    /** Identifies one viewport within the shared workspace scene. */
    interface Props {
        /** Camera orientation used by this viewport. */
        cameraMode: CameraMode;
    }
    let { cameraMode }: Props = $props();
    const getLayout = usePointCloudWorkspaceLayoutContext();
    const layout = $derived(getLayout());
    const annotations = $derived(layout.transforms.annotations);
    const scene = useWorkspaceSceneLayout();
    const labels = { perspective: '3D scene', top: 'Top', side: 'Side', front: 'Front' };
</script>

<SceneViewport
    batch={layout.sceneFrame?.batch}
    colorMode={layout.colorMode}
    pointCloudBounds={layout.sceneFrame?.bounds ?? undefined}
    fitKey={layout.fitKey}
    cuboids={$annotations}
    annotationClasses={layout.annotationClasses}
    annotationSources={layout.annotationSources}
    transforms={layout.transforms}
    pointSize={layout.pointSize}
    showNavigationHelpers={layout.showNavigationHelpers}
    showAnnotationTooltips={layout.showAnnotationTooltips}
    showActiveBorder={layout.showOrthographicViews}
    selectedAnnotationId={layout.selectedCuboidId}
    hoveredAnnotationId={layout.hoveredCuboidId}
    activeTool={layout.effectiveTool}
    {cameraMode}
    isScaleSource={cameraMode === 'perspective' || scene.expandedProjection === cameraMode}
    onselect={layout.onSelect}
    onhover={(id) => layout.onHover(id)}
    onCreateCuboid={layout.onCreateCuboid}
    onPreviousTick={cameraMode === 'perspective' ? layout.onPreviousFrame : undefined}
    onNextTick={cameraMode === 'perspective' ? layout.onNextFrame : undefined}
>
    {#snippet header()}
        {#if cameraMode === 'perspective'}
            <WorkspaceSceneHeader />
        {:else}
            <div class="pointer-events-none flex items-start justify-between px-2 py-1">
                <span class="rounded bg-background/80 px-1.5 py-0.5 text-xs text-muted-foreground"
                    >{labels[cameraMode]}</span
                >
                <div class="pointer-events-auto">
                    <ViewportExpandButton
                        expanded={scene.expandedProjection === cameraMode}
                        label={labels[cameraMode]}
                        onToggle={() => scene.toggleExpanded(cameraMode)}
                    />
                </div>
            </div>
        {/if}
    {/snippet}
    {#snippet tools()}
        {#if cameraMode === 'perspective' && layout.isEditingMode}
            <ToolRail activeTool={layout.activeTool} onToolChange={layout.onToolChange} />
        {/if}
    {/snippet}
</SceneViewport>
