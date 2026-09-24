<script lang="ts">
    import { Pane, PaneGroup, PaneResizer } from 'paneforge';
    import WorkspaceHeader from './WorkspaceHeader/WorkspaceHeader.svelte';
    import WorkspaceFilterBar from './WorkspaceFilterBar/WorkspaceFilterBar.svelte';
    import ToolRail from './ToolRail/ToolRail.svelte';
    import SceneViewport from './SceneViewport/SceneViewport.svelte';
    import CameraProjectionStrip from './CameraProjectionStrip/CameraProjectionStrip.svelte';
    import PointCloudRightSidePanel from './PointCloudRightSidePanel';
    import FrameTimeline from './FrameTimeline/FrameTimeline.svelte';
    import WorkspaceStatusPanel from './WorkspaceStatusPanel/WorkspaceStatusPanel.svelte';
    import type { WorkspaceCrumb } from './types';
    import { createPointCloudWorkspaceContext } from './provider/createPointCloudWorkspaceContext';

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
        /** Dataset the labeled point-cloud sequence belongs to. */
        datasetId: string;
        /** MCAP sequence being labeled, used to resolve per-tick camera frames. */
        sequenceId: string;
        /** Dataset -> collection -> sample path of the point cloud being labeled. */
        sourcePath?: readonly WorkspaceCrumb[];
        /** Overridable for tests/stories; production always starts at `empty` today. */
        status?: 'unsupported' | 'empty' | 'error';
        onExit?: () => void;
        onRetry?: () => void;
    }

    let {
        sampleId,
        datasetId,
        sequenceId,
        sourcePath = [],
        status,
        onExit = () => undefined,
        onRetry
    }: Props = $props();

    const workspace = createPointCloudWorkspaceContext(() => ({
        datasetId,
        sequenceId,
        statusOverride: status
    }));

    let selectedCuboidId = $state<string | null>(null);

    let containerEl = $state<HTMLDivElement | undefined>(undefined);
    let isFullscreen = $state(false);

    // Channel data lands with browser-side MCAP loading (later child issues of LIG-10657); until
    // then the filter bar renders empty but its selection state is already owned here.
    let selectedLidarChannels = $state<number[]>([]);
    let selectedCameraChannels = $state<number[]>([]);

    const lidarChannels = $derived(workspace.lidarChannels);
    const cameraChannels = $derived(workspace.cameraChannels);

    const toggleChannel = (selected: number[], channelId: number): number[] =>
        selected.includes(channelId)
            ? selected.filter((id) => id !== channelId)
            : [...selected, channelId];

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
    <WorkspaceFilterBar
        {lidarChannels}
        {cameraChannels}
        {selectedLidarChannels}
        {selectedCameraChannels}
        onToggleLidarChannel={(channelId) =>
            (selectedLidarChannels = toggleChannel(selectedLidarChannels, channelId))}
        onToggleCameraChannel={(channelId) =>
            (selectedCameraChannels = toggleChannel(selectedCameraChannels, channelId))}
    />
    <div class="flex min-h-0 flex-1">
        {#if workspace.status === 'unsupported' || workspace.status === 'error'}
            <WorkspaceStatusPanel
                status={workspace.status}
                onRetry={onRetry ?? workspace.retry}
                {onExit}
            />
        {:else}
            <PaneGroup direction="horizontal" class="min-h-0 flex-1">
                <Pane defaultSize={78} minSize={50} class="flex min-h-0 flex-col">
                    <PaneGroup direction="vertical" class="min-h-0 flex-1">
                        <!-- The point cloud dominates: full width of the working column. -->
                        <Pane defaultSize={62} minSize={30} class="relative min-h-0">
                            <ToolRail />
                            {#if workspace.status === 'empty' || workspace.status === 'loading'}
                                <WorkspaceStatusPanel status={workspace.status} {onExit} />
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
                            <CameraProjectionStrip
                                {datasetId}
                                {sequenceId}
                                seqNumber={workspace.currentTick}
                            />
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
                            <FrameTimeline
                                ticks={workspace.ticks}
                                currentTick={workspace.currentTick}
                                isPlaying={workspace.isPlaying}
                                onPreviousFrame={workspace.goToPreviousFrame}
                                onNextFrame={workspace.goToNextFrame}
                                onPlayToggle={workspace.togglePlayback}
                            />
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
                    <PointCloudRightSidePanel bind:selectedCuboidId />
                </Pane>
            </PaneGroup>
        {/if}
    </div>
</div>
