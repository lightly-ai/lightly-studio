<script lang="ts">
    import { Pane, PaneGroup } from 'paneforge';
    import { Separator } from '$lib/components';
    import WorkspaceHeader from './WorkspaceHeader/WorkspaceHeader.svelte';
    import WorkspaceFilterBar from './WorkspaceFilterBar/WorkspaceFilterBar.svelte';
    import ToolRail from './ToolRail/ToolRail.svelte';
    import SceneViewport from './SceneViewport/SceneViewport.svelte';
    import CameraProjectionStrip from './CameraProjectionStrip/CameraProjectionStrip.svelte';
    import PointCloudRightSidePanel from './PointCloudRightSidePanel';
    import FrameTimeline from './FrameTimeline/FrameTimeline.svelte';
    import WorkspaceStatusPanel from './WorkspaceStatusPanel/WorkspaceStatusPanel.svelte';
    import WorkspacePaneResizer from './WorkspacePaneResizer/WorkspacePaneResizer.svelte';
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
     * Loads all lidar payloads for the active tick and renders them in the 3D scene.
     */
    interface Props {
        sampleId: string;
        /** Dataset the labeled point-cloud sequence belongs to. */
        datasetId: string;
        /** MCAP sequence being labeled, used to resolve per-tick camera frames. */
        sequenceId: string;
        /** 1-based tick to open on (from the route hash); defaults to the first frame. */
        tickNumber?: number;
        /** Dataset -> collection -> sample path of the point cloud being labeled. */
        sourcePath?: readonly WorkspaceCrumb[];
        /** Optional status override for tests and stories. */
        status?: 'unsupported' | 'empty' | 'error';
        onExit?: () => void;
        onRetry?: () => void;
    }

    let {
        sampleId,
        datasetId,
        sequenceId,
        tickNumber = 1,
        sourcePath = [],
        status,
        onExit = () => undefined,
        onRetry
    }: Props = $props();

    const workspace = createPointCloudWorkspaceContext(() => ({
        datasetId,
        sequenceId,
        // The hash tick is 1-based; the transport tracks 0-based seq numbers.
        initialTick: tickNumber - 1,
        statusOverride: status
    }));
    let selectedCuboidId = $state<string | null>(null);

    let containerEl = $state<HTMLDivElement | undefined>(undefined);
    let isFullscreen = $state(false);

    // The lidar selection lives in the workspace context because it drives which point clouds
    // load; the camera selection does not filter anything yet, so it stays local.
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
    class="flex h-full min-h-0 w-full min-w-0 flex-col gap-4 rounded-[1vw] bg-card p-4"
    data-testid="point-cloud-labeling-workspace"
>
    <WorkspaceHeader
        {sampleId}
        {sourcePath}
        {isFullscreen}
        onToggleFullscreen={toggleFullscreen}
        {onExit}
    />
    <Separator class="shrink-0 bg-border-hard" />
    <WorkspaceFilterBar
        {lidarChannels}
        {cameraChannels}
        selectedLidarChannels={workspace.selectedLidarChannels}
        {selectedCameraChannels}
        onToggleLidarChannel={(channelId) => workspace.toggleLidarChannel(channelId)}
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
                        <Pane
                            defaultSize={62}
                            minSize={30}
                            class="relative min-h-0 overflow-hidden rounded-lg border border-border-hard bg-background"
                        >
                            <ToolRail />
                            {#if workspace.tickDetails.isError || workspace.cloudPointFrame.isError}
                                <WorkspaceStatusPanel
                                    status="error"
                                    onRetry={workspace.retry}
                                    {onExit}
                                />
                            {:else if workspace.status === 'empty'}
                                <WorkspaceStatusPanel status="empty" {onExit} />
                            {:else if workspace.status === 'loading' || workspace.tickDetails.isLoading || workspace.cloudPointFrame.isLoading}
                                <WorkspaceStatusPanel status="loading" {onExit} />
                            {:else if workspace.cloudPointFrame.data}
                                <SceneViewport
                                    batch={workspace.cloudPointFrame.data.batch}
                                    colorMode={workspace.cloudPointFrame.data.batch.colors
                                        ? 'rgb'
                                        : 'intensity'}
                                />
                            {:else}
                                <WorkspaceStatusPanel status="empty" {onExit} />
                            {/if}
                        </Pane>
                        <WorkspacePaneResizer direction="vertical" />
                        <!-- Cameras and orthographic projections sit directly under the cloud. -->
                        <Pane defaultSize={22} minSize={12} maxSize={45} class="min-h-0">
                            <CameraProjectionStrip
                                {datasetId}
                                {sequenceId}
                                seqNumber={workspace.currentTick}
                            />
                        </Pane>
                        <WorkspacePaneResizer direction="vertical" />
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
                <WorkspacePaneResizer direction="horizontal" />
                <Pane defaultSize={22} minSize={16} maxSize={40}>
                    <PointCloudRightSidePanel bind:selectedCuboidId />
                </Pane>
            </PaneGroup>
        {/if}
    </div>
</div>
