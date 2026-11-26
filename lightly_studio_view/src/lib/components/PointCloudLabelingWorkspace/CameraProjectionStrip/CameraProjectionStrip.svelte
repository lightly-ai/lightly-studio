<script lang="ts">
    import type {
        ChannelSummaryView,
        AnnotationView
    } from '$lib/api/lightly_studio_local/types.gen';
    import type { PointBatch } from '$lib/components/PointCloudViewer';
    import type { AnnotationClassColor } from './projectionOverlay';
    import CameraProjectionFrame from './CameraProjectionFrame/CameraProjectionFrame.svelte';
    import CameraProjectionDialog from './CameraProjectionFrame/CameraProjectionDialog.svelte';
    import { useCameraFrame } from './CameraProjectionFrame/useCameraFrame/useCameraFrame.svelte';
    import { getAdjacentCamera, getCameraForDigit } from './cameraNavigation/cameraNavigation';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useTickCameraFrames, useTickDetails } from '$lib/hooks';
    import ProjectionControls from './ProjectionControls.svelte';
    import ChevronDown from '@lucide/svelte/icons/chevron-down';
    import ChevronUp from '@lucide/svelte/icons/chevron-up';
    import { Button } from '$lib/components';
    import { useProjectionSettings } from './useProjectionSettings/useProjectionSettings.svelte';
    import WorkspacePanelHeader from '../WorkspacePanelHeader/WorkspacePanelHeader.svelte';

    interface Props {
        datasetId: string;
        sequenceId: string;
        seqNumber: number;
        displayFrameId?: string;
        cameraChannels: ChannelSummaryView[];
        selectedChannelIds: number[];
        batch?: PointBatch;
        annotations?: readonly AnnotationView[];
        annotationClasses?: readonly AnnotationClassColor[];
        canProject?: boolean;
        onPlaybackToggle?: () => void;
        collapsed?: boolean;
        onToggleCollapsed?: () => void;
        openCamera?: string;
        onOpenCameraChange?: (camera: string | undefined, history: 'push' | 'replace') => void;
    }

    let {
        datasetId,
        sequenceId,
        seqNumber,
        displayFrameId,
        cameraChannels: summaryCameraChannels,
        selectedChannelIds,
        batch,
        annotations = [],
        annotationClasses = [],
        canProject = true,
        onPlaybackToggle,
        collapsed = false,
        onToggleCollapsed,
        openCamera,
        onOpenCameraChange
    }: Props = $props();
    const projectionSettings = useProjectionSettings();
    const { settingsStore } = useSettings();

    const { tickDetails } = useTickDetails({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getSeqNumber: () => seqNumber,
        getDisplayFrameId: () => displayFrameId || undefined
    });
    const recordingId = $derived(tickDetails.data?.recording_id);
    const { query: cameraFrames } = useTickCameraFrames(() => ({
        datasetId,
        sequenceId,
        seqNumber,
        displayFrameId: displayFrameId || undefined
    }));
    const selectedChannels = $derived(
        summaryCameraChannels.filter((channel) => selectedChannelIds.includes(channel.channel_id))
    );
    const selectedNames = $derived(selectedChannels.map((channel) => channel.group_component_name));
    const openChannel = $derived(
        selectedChannels.find((channel) => channel.group_component_name === openCamera)
    );
    const openChannelDetails = $derived(
        openChannel
            ? tickDetails.data?.camera_channels[openChannel.group_component_name]
            : undefined
    );
    // The same inputs as the open camera's tile, so the dialog follows the current tick.
    const openFrame = useCameraFrame(() => ({
        datasetId,
        recordingId,
        channelId: openChannel?.channel_id ?? 0,
        keyframeTimestampNs: openChannelDetails?.keyframe_log_time_ns ?? undefined,
        logTimeNs: openChannelDetails?.log_time_ns,
        blob: openChannel ? cameraFrames.data?.[openChannel.channel_id] : undefined,
        label: openChannel?.group_component_name ?? ''
    }));

    // Channels load after the route, so an empty list is not a verdict on the open camera.
    $effect(() => {
        if (
            summaryCameraChannels.length > 0 &&
            openCamera !== undefined &&
            !selectedNames.includes(openCamera)
        ) {
            onOpenCameraChange?.(undefined, 'replace');
        }
    });

    function switchCamera(direction: 'previous' | 'next') {
        if (openCamera === undefined) return;
        const camera = getAdjacentCamera(selectedNames, openCamera, direction);
        if (camera !== undefined) onOpenCameraChange?.(camera, 'replace');
    }

    function handleWindowKeydown(event: KeyboardEvent) {
        const isInOtherDialog =
            event.target instanceof Element && event.target.closest('[role="dialog"]') !== null;
        if (openCamera === undefined && isInOtherDialog) return;
        const camera = getCameraForDigit(event, selectedNames);
        if (camera === undefined) return;
        event.preventDefault();
        onOpenCameraChange?.(camera, openCamera ? 'replace' : 'push');
    }
</script>

<svelte:window onkeydown={handleWindowKeydown} />

<div
    class="flex h-full min-h-0 flex-col bg-background"
    class:justify-center={collapsed}
    data-testid="workspace-projection-strip"
>
    <WorkspacePanelHeader title="Camera projections">
        {#snippet actions()}
            <ProjectionControls
                settings={$projectionSettings}
                onChange={(settings) => projectionSettings.set(settings)}
                {onPlaybackToggle}
            />
            {#if onToggleCollapsed}
                <Button
                    variant="ghost"
                    icon={collapsed ? ChevronUp : ChevronDown}
                    ariaLabel={collapsed ? 'Expand camera strip' : 'Collapse camera strip'}
                    buttonProps={{
                        type: 'button',
                        size: 'xs',
                        class: 'h-7 w-7 p-0',
                        onclick: onToggleCollapsed
                    }}
                />
            {/if}
        {/snippet}
    </WorkspacePanelHeader>
    {#if !collapsed}
        <!-- Reserve scrollbar height so resizing the tiles cannot toggle overflow in a loop. -->
        <div class="scrollbar-thin flex min-h-0 flex-1 gap-2 overflow-x-scroll px-2 pb-2">
            {#each selectedChannels as summaryChannel}
                {@const channel =
                    tickDetails.data?.camera_channels[summaryChannel.group_component_name]}
                <CameraProjectionFrame
                    {datasetId}
                    {recordingId}
                    channelId={summaryChannel.channel_id}
                    keyframeTimestampNs={channel?.keyframe_log_time_ns ?? undefined}
                    logTimeNs={channel?.log_time_ns}
                    blob={cameraFrames.data?.[summaryChannel.channel_id]}
                    label={summaryChannel.group_component_name}
                    {batch}
                    {annotations}
                    {annotationClasses}
                    projection={canProject ? (channel?.projection ?? undefined) : undefined}
                    projectionSettings={$projectionSettings}
                    onEnlarge={() =>
                        onOpenCameraChange?.(summaryChannel.group_component_name, 'push')}
                />
            {/each}
        </div>
    {/if}
</div>
<!-- One dialog for every camera, so switching cameras and ticks never remounts it. -->
<CameraProjectionDialog
    bind:open={
        () => openChannel !== undefined,
        (open) => {
            if (!open) onOpenCameraChange?.(undefined, 'replace');
        }
    }
    label={openChannel?.group_component_name ?? ''}
    imageUrl={openFrame.fullFrameUrl ?? openFrame.frameUrl}
    {batch}
    {annotations}
    {annotationClasses}
    projection={canProject ? (openChannelDetails?.projection ?? undefined) : undefined}
    projectionSettings={$projectionSettings}
    onProjectionSettingsChange={(settings) => projectionSettings.set(settings)}
    {onPlaybackToggle}
    position={{
        index: openCamera === undefined ? 0 : selectedNames.indexOf(openCamera) + 1,
        total: selectedNames.length
    }}
    onPrevious={selectedNames.length > 1 ? () => switchCamera('previous') : undefined}
    onNext={selectedNames.length > 1 ? () => switchCamera('next') : undefined}
    previousKey={$settingsStore.key_previous_camera}
    nextKey={$settingsStore.key_next_camera}
/>
