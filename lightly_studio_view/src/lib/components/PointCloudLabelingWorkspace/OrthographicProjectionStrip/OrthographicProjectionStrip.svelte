<script lang="ts">
    import WorkspaceViewport from '../WorkspaceViewport/WorkspaceViewport.svelte';
    import { useWorkspaceSceneLayout } from '../workspaceSceneLayoutContext.svelte';
    import { usePointCloudWorkspaceLayoutContext } from '../pointCloudWorkspaceLayoutContext.svelte';
    import { cn } from '$lib/utils';
    import { WorkspacePanel } from '../WorkspacePanel';
    const scene = useWorkspaceSceneLayout();
    const getLayout = usePointCloudWorkspaceLayoutContext();
    const layout = $derived(getLayout());
    const views = ['top', 'side', 'front'] as const;
</script>

<WorkspacePanel
    title="Orthographic views"
    onHide={() => layout.onToggleOrthographicProjections(false)}
    class="h-full"
    testId="orthographic-views-panel"
>
    <!-- The 1px gaps show the border color between the views, so the panel reads as one card. -->
    <div
        class={cn(
            'grid h-full min-h-0 bg-border',
            scene.expandedProjection ? 'grid-cols-1' : 'grid-cols-3 gap-px'
        )}
    >
        {#each views as mode (mode)}
            <div
                class="relative min-h-0 min-w-0 overflow-hidden"
                hidden={scene.expandedProjection !== null && scene.expandedProjection !== mode}
                data-testid={`projection-${mode}`}
            >
                <WorkspaceViewport cameraMode={mode} />
            </div>
        {/each}
    </div>
</WorkspacePanel>
