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
    import type { PointCloudWorkspaceContext } from './provider/types';
    import type { ColorMode } from '$lib/components/PointCloudViewer';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { getColorByLabel } from '$lib/utils';
    import { useAnnotationCollections } from '$lib/hooks';
    import { tickAnnotationsToClasses, tickAnnotationsToCuboids } from './tickAnnotationsToCuboids';
    import { useChannelSelection } from './useChannelSelection.svelte';

    /**
     * Feature-gated, lazy-loaded shell for browser-side point-cloud labeling (LIG-10659).
     *
     * Layout, top to bottom: source breadcrumb, fast-filter strip, then a working column whose 3D
     * viewport takes the full width and most of the height, with the camera/projection strip
     * beneath it and the frame timeline at the bottom. The tags and annotations of the active tick
     * stay in a resizable right pane, and the tool rail floats over the viewport rather than taking
     * a column of its own.
     *
     * Loads the selected LiDAR payloads for the active tick and renders them in the 3D scene.
     */
    interface Props {
        /** Dataset the labeled point-cloud sequence belongs to. */
        datasetId: string;
        /** GROUP collection containing the point cloud annotation sources. */
        annotationSourceCollectionId?: string;
        /** MCAP sequence being labeled, used to resolve per-tick camera frames. */
        sequenceId: string;
        /** 1-based tick to open on (from the route hash); defaults to the first frame. */
        tickNumber?: number;
        /** Reports the active tick as a 1-based number for route synchronization. */
        onTickChange?: (tickNumber: number) => void;
        /** Opens the previous sequence; the timeline control is disabled when absent. */
        onPreviousSequence?: () => void;
        /** Opens the next sequence; the timeline control is disabled when absent. */
        onNextSequence?: () => void;
        /** Dataset -> collection -> sample path of the point cloud being labeled. */
        sourcePath?: readonly WorkspaceCrumb[];
        /** Optional status override for tests and stories. */
        status?: 'unsupported' | 'empty' | 'error';
        onRetry?: () => void;
    }

    let {
        datasetId,
        annotationSourceCollectionId,
        sequenceId,
        tickNumber = 1,
        onTickChange = () => undefined,
        onPreviousSequence,
        onNextSequence,
        sourcePath = [],
        status,
        onRetry
    }: Props = $props();

    let selectedColorMode = $state<Exclude<ColorMode, 'none'> | null>(null);

    let workspace = $state<PointCloudWorkspaceContext>({} as PointCloudWorkspaceContext);
    const lidarSelection = useChannelSelection({
        getChannels: () => workspace.lidarChannels,
        getResetKey: () => sequenceId
    });
    const cameraSelection = useChannelSelection({
        getChannels: () => workspace.cameraChannels,
        getResetKey: () => sequenceId
    });

    workspace = createPointCloudWorkspaceContext(() => ({
        datasetId,
        sequenceId,
        selectedLidarChannels: lidarSelection.selectedChannels ?? undefined,
        // The hash tick is 1-based; the transport tracks 0-based seq numbers.
        initialTick: tickNumber - 1,
        statusOverride: status
    }));
    const { goToPreviousFrame, goToNextFrame, goToFrame, togglePlayback } =
        usePointCloudTickNavigation({
            getWorkspace: () => workspace,
            getTickNumber: () => tickNumber,
            getOnTickChange: () => onTickChange
        });
    let selectedCuboidId = $state<string | null>(null);
    let hoveredCuboidId = $state<string | null>(null);
    const { customLabelColorsStore } = useCustomLabelColors();
    const annotationCollectionsQuery = useAnnotationCollections(() => ({
        collectionId: annotationSourceCollectionId
    }));
    const annotationSources = $derived(
        (annotationCollectionsQuery.data ?? []).map(({ collection_id, name }) => ({
            id: collection_id,
            name
        }))
    );

    // Synchronized snapshot: the cloud frame and its corresponding annotations
    // advance together.
    let sceneSnapshot = $state<{
        frame: NonNullable<(typeof workspace.cloudPointFrame)['data']>;
        annotations: Parameters<typeof tickAnnotationsToCuboids>[0];
    } | null>(null);

    $effect(() => {
        if (
            workspace.cloudPointFrame.data &&
            !workspace.cloudPointFrame.isPlaceholderData &&
            !workspace.tickDetails.isPlaceholderData
        ) {
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

    const tick = $derived.by(() => {
        const details = workspace.tickDetails.data;
        return details
            ? {
                  sampleId: details.sample_id,
                  collectionId: details.collection_id,
                  tags: details.tags,
                  // Placeholder data belongs to the previous tick, so it must not be edited.
                  isStale: workspace.tickDetails.isPlaceholderData
              }
            : undefined;
    });

    let containerEl = $state<HTMLDivElement | undefined>(undefined);
    let isFullscreen = $state(false);

    const lidarChannels = $derived(workspace.lidarChannels);
    const cameraChannels = $derived(workspace.cameraChannels);
    const displayedColorMode = $derived(selectedColorMode ?? 'density');

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
        selectedLidarChannels={lidarSelection.selectedChannelIds}
        selectedCameraChannels={cameraSelection.selectedChannelIds}
        colorMode={displayedColorMode}
        onColorModeChange={(mode) => (selectedColorMode = mode)}
        onToggleLidarChannel={lidarSelection.toggleChannel}
        onToggleCameraChannel={cameraSelection.toggleChannel}
        onSetLidarChannels={lidarSelection.setChannels}
        onSetCameraChannels={cameraSelection.setChannels}
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
                                    {annotationSources}
                                    selectedAnnotationId={selectedCuboidId}
                                    hoveredAnnotationId={hoveredCuboidId}
                                    onselect={(id) => (selectedCuboidId = id)}
                                    onhover={(id) => (hoveredCuboidId = id)}
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
                                cameraChannels={workspace.cameraChannels}
                                seqNumber={workspace.currentTick}
                                displayFrameId={workspace.referenceFrameId}
                                selectedChannelIds={cameraSelection.selectedChannelIds}
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
                                onPreviousFrame={goToPreviousFrame}
                                onNextFrame={goToNextFrame}
                                onPlayToggle={togglePlayback}
                                onPlaybackIntervalChange={workspace.setPlaybackIntervalMs}
                                onSelectTick={goToFrame}
                                {onPreviousSequence}
                                {onNextSequence}
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
                    <PointCloudRightSidePanel
                        {cuboids}
                        {annotationClasses}
                        {annotationSources}
                        bind:selectedCuboidId
                        {tick}
                        onTagsChange={() => void workspace.tickDetails.refetch()}
                    />
                </Pane>
            </PaneGroup>
        {/if}
    </div>
</div>
