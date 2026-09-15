<script lang="ts">
    import { Pane, PaneGroup, PaneResizer } from 'paneforge';
    import WorkspaceHeader from './WorkspaceHeader/WorkspaceHeader.svelte';
    import WorkspaceFilterBar from './WorkspaceFilterBar/WorkspaceFilterBar.svelte';
    import ToolRail from './ToolRail/ToolRail.svelte';
    import SceneViewport from './SceneViewport/SceneViewport.svelte';
    import CameraProjectionStrip from './CameraProjectionStrip/CameraProjectionStrip.svelte';
    import AnnotationPanel from './AnnotationPanel/AnnotationPanel.svelte';
    import FrameTimeline from './FrameTimeline/FrameTimeline.svelte';
    import WorkspaceStatusPanel from './WorkspaceStatusPanel/WorkspaceStatusPanel.svelte';
    import type { WorkspaceCrumb } from './types';

    /**
     * Feature-gated, lazy-loaded shell for browser-side point-cloud labeling (LIG-10659).
     *
     * Layout, top to bottom: source breadcrumb, fast-filter strip, then a working column whose 3D
     * viewport takes the full width and most of the height, with the camera/projection strip
     * beneath it and the frame timeline at the bottom. Annotations stay in a resizable right pane,
     * and the tool rail floats over the viewport rather than taking a column of its own.
     *
     * This issue only delivers the route and composed placeholders: browser-side MCAP frame
     * loading, the Three.js scene, and persistence land in later child issues of LIG-10657. Until
     * then `status` defaults to `empty` so the chrome (breadcrumb, filters, resizable panels,
     * fullscreen, timeline) is fully in place and testable ahead of real data.
     */
    interface Props {
        sampleId: string;
        /** Dataset -> collection -> sample path of the point cloud being labeled. */
        sourcePath?: readonly WorkspaceCrumb[];
        /** Overridable for tests/stories; production always starts at `empty` today. */
        status?: 'unsupported' | 'empty' | 'error';
        onExit: () => void;
        onRetry?: () => void;
    }

    let { sampleId, sourcePath = [], status = 'empty', onExit, onRetry }: Props = $props();

    let containerEl = $state<HTMLDivElement | undefined>(undefined);
    let isFullscreen = $state(false);

    const handleFullscreenChange = () => {
        isFullscreen = document.fullscreenElement === containerEl;
    };

    const toggleFullscreen = async () => {
        if (!containerEl) return;
        if (document.fullscreenElement) {
            await document.exitFullscreen();
        } else {
            await containerEl.requestFullscreen();
        }
    };

    $effect(() => {
        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
    });
</script>

<div
    bind:this={containerEl}
    class="flex h-full min-h-0 w-full min-w-0 flex-col bg-background"
    data-testid="point-cloud-labeling-workspace"
>
    <WorkspaceHeader
        {sampleId}
        {sourcePath}
        {isFullscreen}
        onToggleFullscreen={toggleFullscreen}
        {onExit}
    />
    <WorkspaceFilterBar />
    <div class="flex min-h-0 flex-1">
        {#if status === 'unsupported' || status === 'error'}
            <WorkspaceStatusPanel {status} {onRetry} {onExit} />
        {:else}
            <PaneGroup direction="horizontal" class="min-h-0 flex-1">
                <Pane defaultSize={78} minSize={50} class="flex min-h-0 flex-col">
                    <PaneGroup direction="vertical" class="min-h-0 flex-1">
                        <!-- The point cloud dominates: full width of the working column. -->
                        <Pane defaultSize={62} minSize={30} class="relative min-h-0">
                            <ToolRail />
                            {#if status === 'empty'}
                                <WorkspaceStatusPanel status="empty" {onExit} />
                            {:else}
                                <SceneViewport />
                            {/if}
                        </Pane>
                        <PaneResizer
                            class="group relative flex h-2 cursor-row-resize items-center justify-center bg-border/50 transition-colors hover:bg-border"
                        >
                            <div
                                class="flex gap-0.5 opacity-40 transition-opacity group-hover:opacity-100"
                            >
                                <span class="size-1 rounded-full bg-muted-foreground"></span>
                                <span class="size-1 rounded-full bg-muted-foreground"></span>
                                <span class="size-1 rounded-full bg-muted-foreground"></span>
                            </div>
                        </PaneResizer>
                        <!-- Cameras and orthographic projections sit directly under the cloud. -->
                        <Pane defaultSize={22} minSize={12} maxSize={45} class="min-h-0">
                            <CameraProjectionStrip />
                        </Pane>
                        <PaneResizer
                            class="group relative flex h-2 cursor-row-resize items-center justify-center bg-border/50 transition-colors hover:bg-border"
                        >
                            <div
                                class="flex gap-0.5 opacity-40 transition-opacity group-hover:opacity-100"
                            >
                                <span class="size-1 rounded-full bg-muted-foreground"></span>
                                <span class="size-1 rounded-full bg-muted-foreground"></span>
                                <span class="size-1 rounded-full bg-muted-foreground"></span>
                            </div>
                        </PaneResizer>
                        <Pane defaultSize={16} minSize={10} maxSize={40} class="min-h-0">
                            <FrameTimeline />
                        </Pane>
                    </PaneGroup>
                </Pane>
                <PaneResizer
                    class="group relative flex w-2 cursor-col-resize items-center justify-center bg-border/50 transition-colors hover:bg-border"
                >
                    <div
                        class="flex flex-col gap-0.5 opacity-40 transition-opacity group-hover:opacity-100"
                    >
                        <span class="size-1 rounded-full bg-muted-foreground"></span>
                        <span class="size-1 rounded-full bg-muted-foreground"></span>
                        <span class="size-1 rounded-full bg-muted-foreground"></span>
                    </div>
                </PaneResizer>
                <Pane defaultSize={22} minSize={16} maxSize={40}>
                    <AnnotationPanel />
                </Pane>
            </PaneGroup>
        {/if}
    </div>
</div>
