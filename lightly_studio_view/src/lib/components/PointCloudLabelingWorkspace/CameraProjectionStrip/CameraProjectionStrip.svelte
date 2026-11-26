<script lang="ts">
    import type {
        ChannelSummaryView,
        AnnotationView
    } from '$lib/api/lightly_studio_local/types.gen';
    import type { PointBatch } from '$lib/components/PointCloudViewer';
    import type { AnnotationClassColor } from './projectionOverlay';
    import CameraProjectionFrame from './CameraProjectionFrame/CameraProjectionFrame.svelte';
    import { useTickCameraFrames, useTickDetails } from '$lib/hooks';
    import ProjectionControls from './ProjectionControls.svelte';
    import { useProjectionSettings } from './useProjectionSettings/useProjectionSettings.svelte';
    import { WorkspacePanel } from '../WorkspacePanel';
    import { PanelDockToggle, type PanelDock } from '../PanelDockToggle';
    import { WorkspaceChannelSelect } from '../WorkspaceChannelSelect';
    import { cn } from '$lib/utils';

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
        /** Hides the strip; the panel shows no close button without it. */
        onHide?: () => void;
        /** Where the strip sits: below the scene (tiles in a row) or on its right (in a column). */
        dock?: PanelDock;
        /** Moves the strip; the panel shows no dock toggle without it. */
        onDockChange?: (dock: PanelDock) => void;
        /** Toggles a camera channel; the settings show no channel select without it. */
        onToggleCameraChannel?: (channelId: number) => void;
        /** Replaces the shown camera channels. */
        onSetCameraChannels?: (channelIds: number[]) => void;
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
        onHide,
        dock = 'bottom',
        onDockChange,
        onToggleCameraChannel,
        onSetCameraChannels
    }: Props = $props();
    const projectionSettings = useProjectionSettings();

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
</script>

{#snippet cameraChannelSelect()}
    {#if onToggleCameraChannel && onSetCameraChannels}
        <WorkspaceChannelSelect
            label="Camera"
            channels={summaryCameraChannels}
            selectedChannels={selectedChannelIds}
            onToggleChannel={onToggleCameraChannel}
            onSetChannels={onSetCameraChannels}
            testId="workspace-camera-select"
        />
    {/if}
{/snippet}

<WorkspacePanel
    title="Camera projections"
    {onHide}
    class="h-full"
    testId="workspace-projection-strip"
>
    {#snippet actions()}
        <ProjectionControls
            settings={$projectionSettings}
            onChange={(settings) => projectionSettings.set(settings)}
            {onPlaybackToggle}
            filters={onToggleCameraChannel && onSetCameraChannels ? cameraChannelSelect : undefined}
        />
        {#if onDockChange}
            <PanelDockToggle {dock} label="camera projections" onChange={onDockChange} />
        {/if}
    {/snippet}
    <!-- Reserve the scrollbar so resizing the tiles cannot toggle overflow in a loop. -->
    <div
        class={cn(
            'scrollbar-thin flex h-full min-h-0 gap-2 px-2 pb-2',
            dock === 'right' ? 'flex-col overflow-x-hidden overflow-y-scroll' : 'overflow-x-scroll'
        )}
    >
        {#each summaryCameraChannels.filter( (channel) => selectedChannelIds.includes(channel.channel_id) ) as summaryChannel (summaryChannel.channel_id)}
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
                {onPlaybackToggle}
                projectionSettings={$projectionSettings}
                onProjectionSettingsChange={(settings) => projectionSettings.set(settings)}
                layout={dock === 'right' ? 'column' : 'row'}
            />
        {/each}
    </div>
</WorkspacePanel>
