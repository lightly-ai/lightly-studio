<script lang="ts">
    import { Pane, PaneGroup, PaneResizer } from 'paneforge';
    import { cn } from '$lib/utils';
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
    const orthographicIsRight = $derived(layout.orthographicDock === 'right');
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
        <!-- A hidden pane gives its space to the other one; both stay mounted so cameras keep their pose. -->
        <PaneGroup
            direction={orthographicIsRight ? 'horizontal' : 'vertical'}
            class="min-h-0 flex-1"
        >
            <Pane
                order={1}
                defaultSize={60}
                minSize={20}
                class="relative min-h-0"
                hidden={scene.expandedProjection !== null &&
                    scene.expandedProjection !== 'perspective'}
            >
                <WorkspaceViewport cameraMode="perspective" />
            </Pane>
            {#if layout.showOrthographicViews}
                <PaneResizer
                    class={cn(
                        'group relative flex items-center justify-center bg-card transition-colors hover:bg-card [&[hidden]]:hidden',
                        orthographicIsRight ? 'w-2 cursor-col-resize' : 'h-2 cursor-row-resize'
                    )}
                    hidden={scene.expandedProjection !== null}
                >
                    <div
                        class={cn(
                            'flex gap-0.5 opacity-40 transition-opacity group-hover:opacity-100',
                            orthographicIsRight && 'flex-col'
                        )}
                    >
                        <span class="size-1 rounded-full bg-muted-foreground"></span>
                        <span class="size-1 rounded-full bg-muted-foreground"></span>
                        <span class="size-1 rounded-full bg-muted-foreground"></span>
                    </div>
                </PaneResizer>
                <Pane
                    order={2}
                    defaultSize={40}
                    minSize={15}
                    class="min-h-0"
                    hidden={scene.expandedProjection === 'perspective'}
                >
                    <OrthographicProjectionStrip />
                </Pane>
            {/if}
        </PaneGroup>
    {:else if layout.workspace.status === 'loading' || layout.workspace.tickDetails.isLoading || layout.workspace.cloudPointFrame.isLoading}
        <WorkspaceStatusPanel status="loading" />
    {:else}
        <WorkspaceStatusPanel status="empty" />
    {/if}
</div>
