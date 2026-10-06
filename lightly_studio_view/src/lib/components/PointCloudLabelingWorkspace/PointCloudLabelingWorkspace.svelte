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
    import { usePointCloudTickNavigation } from './usePointCloudTickNavigation.svelte';
    import type { ColorMode } from '$lib/components/PointCloudViewer';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { getColorByLabel } from '$lib/utils';
    import { tickAnnotationsToClasses, tickAnnotationsToCuboids } from './tickAnnotationsToCuboids';

    /**
     * Feature-gated, lazy-loaded shell for browser-side point-cloud labeling (LIG-10659).
     *
     * Layout, top to bottom: source breadcrumb, fast-filter strip, then a working column whose 3D
     * viewport takes the full width and most of the height, with the camera/projection strip
     * beneath it and the frame timeline at the bottom. Annotations stay in a resizable right pane,
     * and the tool rail floats over the viewport rather than taking a column of its own.
     *
     * Loads the selected LiDAR payloads for the active tick and renders them in the 3D scene.
     */
    interface Props {
        /** Dataset the labeled point-cloud sequence belongs to. */
        datasetId: string;
        /** MCAP sequence being labeled, used to resolve per-tick camera frames. */
        sequenceId: string;
        /** 1-based tick to open on (from the route hash); defaults to the first frame. */
        tickNumber?: number;
        /** Reports the active tick as a 1-based number for route synchronization. */
        onTickChange?: (tickNumber: number) => void;
        /** Dataset -> collection -> sample path of the point cloud being labeled. */
        sourcePath?: readonly WorkspaceCrumb[];
        /** Optional status override for tests and stories. */
        status?: 'unsupported' | 'empty' | 'error';
        onRetry?: () => void;
    }

    let {
        datasetId,
        sequenceId,
        tickNumber = 1,
        onTickChange = () => undefined,
        sourcePath = [],
        status,
        onRetry
    }: Props = $props();

    let selectedLidarChannels = $state<number[] | null>(null);
    let selectedCameraChannels = $state<number[]>([]);
    let selectedColorMode = $state<Exclude<ColorMode, 'none'> | null>(null);

    const workspace = createPointCloudWorkspaceContext(() => ({
        datasetId,
        sequenceId,
        selectedLidarChannels: selectedLidarChannels ?? undefined,
        // The hash tick is 1-based; the transport tracks 0-based seq numbers.
        initialTick: tickNumber - 1,
        statusOverride: status
    }));
    const { goToPreviousFrame, goToNextFrame, goToFrame, togglePlayback } =
        usePointCloudTickNavigation({
            workspace,
            getTickNumber: () => tickNumber,
            getOnTickChange: () => onTickChange
        });
    let selectedCuboidId = $state<string | null>(null);
    const { customLabelColorsStore } = useCustomLabelColors();

    // Synchronized snapshot: the cloud frame and its corresponding annotations
    // advance together.
    let sceneSnapshot = $state<{
        frame: NonNullable<(typeof workspace.cloudPointFrame)['data']>;
        annotations: Parameters<typeof tickAnnotationsToCuboids>[0];
    } | null>(null);

    $effect(() => {
        if (workspace.cloudPointFrame.data && !workspace.cloudPointFrame.isPlaceholderData) {
            sceneSnapshot = {
                frame: workspace.cloudPointFrame.data,
                annotations: workspace.tickDetails.data?.annotations ?? []
            };
        }
    });

    const cuboids = $derived(tickAnnotationsToCuboids(sceneSnapshot?.annotations ?? []));

    const annotationClasses = $derived.by(() => {
        void $customLabelColorsStore;
        return tickAnnotationsToClasses(
            sceneSnapshot?.annotations ?? [],
            (name) => getColorByLabel(name, 1).color
        );
    });

    // Skip cuboids whose coordinate frame differs from the loaded point cloud.
    // When the cloud falls back to sensor frames (no TF transform available),
    // cuboids requested in the reference frame are filtered out rather than
    // rendered at wrong coordinates.
    const sceneCuboids = $derived.by(() => {
        const frameIds = new Set(sceneSnapshot?.frame.channels.map((c) => c.frameId));
        return cuboids.filter((c) => frameIds.has(c.frameId));
    });

    let containerEl = $state<HTMLDivElement | undefined>(undefined);
    let isFullscreen = $state(false);

    const lidarChannels = $derived(workspace.lidarChannels);
    const cameraChannels = $derived(workspace.cameraChannels);
    const displayedColorMode = $derived(selectedColorMode ?? 'density');

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
        if (!datasetId || !sequenceId) return;
        selectedLidarChannels = null;
    });

    $effect(() => {
        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
    });
</script>

<div
    bind:this={containerEl}
    class="flex h-full min-h-0 w-full min-w-0 flex-col"
    data-testid="point-cloud-labeling-workspace"
>
    <WorkspaceHeader
        {sequenceId}
        {sourcePath}
        {isFullscreen}
        onToggleFullscreen={toggleFullscreen}
    />
    <WorkspaceFilterBar
        referenceFrames={workspace.referenceFrames}
        referenceFrameId={workspace.referenceFrameId}
        onSelectReferenceFrame={workspace.selectReferenceFrame}
        isShowingSensorFrames={workspace.isShowingSensorFrames}
        {lidarChannels}
        {cameraChannels}
        selectedLidarChannels={selectedLidarChannels ??
            lidarChannels.map((channel) => channel.channel_id)}
        {selectedCameraChannels}
        colorMode={displayedColorMode}
        onColorModeChange={(mode) => (selectedColorMode = mode)}
        onToggleLidarChannel={(channelId) =>
            (selectedLidarChannels = toggleChannel(
                selectedLidarChannels ?? lidarChannels.map((channel) => channel.channel_id),
                channelId
            ))}
        onToggleCameraChannel={(channelId) =>
            (selectedCameraChannels = toggleChannel(selectedCameraChannels, channelId))}
    />
    <div class="flex min-h-0 flex-1">
        {#if workspace.status === 'unsupported' || workspace.status === 'error'}
            <WorkspaceStatusPanel status={workspace.status} onRetry={onRetry ?? workspace.retry} />
        {:else}
            <PaneGroup direction="horizontal" class="min-h-0 flex-1">
                <Pane defaultSize={78} minSize={50} class="flex min-h-0 flex-col">
                    <PaneGroup direction="vertical" class="min-h-0 flex-1">
                        <!-- The point cloud dominates: full width of the working column. -->
                        <Pane defaultSize={62} minSize={30} class="relative min-h-0">
                            <ToolRail />
                            {#if workspace.tickDetails.isError || workspace.cloudPointFrame.isError}
                                <WorkspaceStatusPanel status="error" onRetry={workspace.retry} />
                            {:else if workspace.status === 'empty'}
                                <WorkspaceStatusPanel status="empty" />
                            {:else if sceneSnapshot}
                                <SceneViewport
                                    batch={sceneSnapshot.frame.batch}
                                    colorMode={displayedColorMode}
                                    pointCloudBounds={sceneSnapshot.frame.bounds ?? undefined}
                                    fitKey={`${sequenceId}/${workspace.referenceFrameId}/${workspace.isShowingSensorFrames}`}
                                    cuboids={sceneCuboids}
                                    {annotationClasses}
                                    selectedAnnotationId={selectedCuboidId}
                                    onselect={(id) => (selectedCuboidId = id)}
                                />
                            {:else if workspace.status === 'loading' || workspace.tickDetails.isLoading || workspace.cloudPointFrame.isLoading}
                                <WorkspaceStatusPanel status="loading" />
                            {:else}
                                <WorkspaceStatusPanel status="empty" />
                            {/if}
                        </Pane>
                        <PaneResizer
                            class="group relative flex h-2 cursor-row-resize items-center justify-center bg-card transition-colors hover:bg-card"
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
                                displayFrameId={workspace.referenceFrameId}
                            />
                        </Pane>
                        <PaneResizer
                            class="group relative flex h-2 cursor-row-resize items-center justify-center bg-card transition-colors hover:bg-card"
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
                                playbackIntervalMs={workspace.playbackIntervalMs}
                                lidarChannelNames={lidarChannels.map(
                                    (channel) => channel.group_component_name
                                )}
                                cameraChannelNames={cameraChannels.map(
                                    (channel) => channel.group_component_name
                                )}
                                onPreviousFrame={goToPreviousFrame}
                                onNextFrame={goToNextFrame}
                                onPlayToggle={togglePlayback}
                                onPlaybackIntervalChange={workspace.setPlaybackIntervalMs}
                                onSelectTick={goToFrame}
                            />
                        </Pane>
                    </PaneGroup>
                </Pane>
                <PaneResizer
                    class="group relative flex w-2 cursor-col-resize items-center justify-center bg-card transition-colors hover:bg-card"
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
                    <PointCloudRightSidePanel {cuboids} {annotationClasses} bind:selectedCuboidId />
                </Pane>
            </PaneGroup>
        {/if}
    </div>
</div>
