<script lang="ts">
    import { Pane, PaneGroup, PaneResizer } from 'paneforge';
    import CameraProjectionStrip from './CameraProjectionStrip/CameraProjectionStrip.svelte';
    import FrameTimeline from './FrameTimeline/FrameTimeline.svelte';
    import PointCloudWorkspaceScene from './PointCloudWorkspaceScene/PointCloudWorkspaceScene.svelte';
    import {
        usePointCloudWorkspaceLayoutContext,
        useWorkspaceControllerContext
    } from './pointCloudWorkspaceLayoutContext.svelte';
    import { useTickDetails, useTickCameraFrames } from '$lib/hooks';
    import { useCameraRgbColors, provideCameraRgbColors } from './useCameraRgbColors';
    import { useSequenceTracks } from './FrameTimeline/useSequenceTracks.svelte';

    const { cameraPane } = useWorkspaceControllerContext();
    const getLayout = usePointCloudWorkspaceLayoutContext();
    const layout = $derived(getLayout());
    const tracksQuery = useSequenceTracks(() => ({
        datasetId: layout.datasetId,
        sequenceId: layout.sequenceId
    }));

    const { tickDetails } = useTickDetails({
        getDatasetId: () => layout.datasetId,
        getSequenceId: () => layout.sequenceId,
        getSeqNumber: () => layout.workspace.currentTick,
        getDisplayFrameId: () => layout.workspace.referenceFrameId || undefined
    });
    const { query: cameraFrames } = useTickCameraFrames(() => ({
        datasetId: layout.datasetId,
        sequenceId: layout.sequenceId,
        seqNumber: layout.workspace.currentTick,
        displayFrameId: layout.workspace.referenceFrameId || undefined
    }));

    const cameraPairs = $derived(
        layout.workspace.isShowingSensorFrames
            ? []
            : layout.workspace.cameraChannels
                  .filter((ch) => layout.selectedCameraChannelIds.includes(ch.channel_id))
                  .flatMap((ch) => {
                      const projection =
                          tickDetails.data?.camera_channels[ch.group_component_name]?.projection;
                      const blob = cameraFrames.data?.[ch.channel_id];
                      return projection && blob ? [{ projection, blob }] : [];
                  })
    );

    const cameraRgb = useCameraRgbColors({
        getBatch: () => layout.sceneFrame?.batch,
        getColorMode: () => layout.colorMode,
        getCameraPairs: () => cameraPairs
    });

    provideCameraRgbColors(() => cameraRgb.colors);
</script>

<PaneGroup direction="vertical" class="min-h-0 flex-1">
    <Pane defaultSize={62} minSize={30} class="min-h-0">
        <div class="flex h-full min-h-0 flex-col">
            <PointCloudWorkspaceScene />
        </div>
    </Pane>
    <PaneResizer
        class="group relative flex h-2 cursor-row-resize items-center justify-center bg-card transition-colors hover:bg-card"
    >
        <div class="flex gap-0.5 opacity-40 transition-opacity group-hover:opacity-100">
            <span class="size-1 rounded-full bg-muted-foreground"></span>
            <span class="size-1 rounded-full bg-muted-foreground"></span>
            <span class="size-1 rounded-full bg-muted-foreground"></span>
        </div>
    </PaneResizer>
    <Pane
        bind:this={cameraPane.pane}
        defaultSize={26}
        minSize={12}
        collapsedSize={4}
        maxSize={45}
        collapsible
        onCollapse={() => layout.onCameraStripCollapsedChange(true)}
        onExpand={() => layout.onCameraStripCollapsedChange(false)}
        class="min-h-0"
    >
        <CameraProjectionStrip
            datasetId={layout.datasetId}
            sequenceId={layout.sequenceId}
            cameraChannels={layout.workspace.cameraChannels}
            seqNumber={layout.workspace.currentTick}
            displayFrameId={layout.workspace.referenceFrameId}
            selectedChannelIds={layout.selectedCameraChannelIds}
            batch={layout.cameraBatch}
            annotations={layout.snapshotAnnotations}
            annotationClasses={layout.annotationClasses}
            canProject={!layout.workspace.isShowingSensorFrames}
            onPlaybackToggle={layout.onPlayToggle}
            collapsed={layout.cameraStripCollapsed}
            onToggleCollapsed={cameraPane.toggle}
        />
    </Pane>
</PaneGroup>

<div class="flex-none">
    {#if tracksQuery.isError}
        <div class="px-2 py-1 text-xs text-destructive">
            Object tracks could not be loaded.
            <button type="button" class="underline" onclick={() => tracksQuery.refetch()}
                >Retry</button
            >
        </div>
    {/if}
    <FrameTimeline
        ticks={layout.workspace.ticks}
        tracks={tracksQuery.data?.tracks ?? []}
        currentTick={layout.workspace.currentTick}
        isPlaying={layout.workspace.isPlaying}
        playbackIntervalMs={layout.workspace.playbackIntervalMs}
        bufferEntireSequence={layout.bufferEntireSequence}
        onBufferEntireSequenceChange={layout.onBufferEntireSequenceChange}
        bufferedRanges={layout.bufferedRanges}
        onPreviousFrame={layout.onPreviousFrame}
        onNextFrame={layout.onNextFrame}
        onPlayToggle={layout.onPlayToggle}
        onPlaybackIntervalChange={layout.onPlaybackIntervalChange}
        onSelectTick={layout.onSelectTick}
        onSeekStart={layout.onSeekStart}
        onSeekEnd={layout.onSeekEnd}
        onPreviousSequence={layout.onPreviousSequence}
        onNextSequence={layout.onNextSequence}
    />
</div>
