<script lang="ts">
    import type { CameraProjectionStripProps } from './cameraProjectionStripProps';
    import CameraProjectionFrame from './CameraProjectionFrame/CameraProjectionFrame.svelte';
    import { useTickCameraFrames, useTickDetails } from '$lib/hooks';
    import ProjectionControls from './ProjectionControls.svelte';
    import { ChevronDown, ChevronUp } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { useProjectionSettings } from './useProjectionSettings/useProjectionSettings.svelte';
    import WorkspacePanelHeader from '../WorkspacePanelHeader/WorkspacePanelHeader.svelte';

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
        onToggleCollapsed
    }: CameraProjectionStripProps = $props();
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
        <div class="scrollbar-thin flex min-h-0 flex-1 gap-2 overflow-x-auto px-2 pb-2">
            {#each summaryCameraChannels.filter( (channel) => selectedChannelIds.includes(channel.channel_id) ) as summaryChannel}
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
                />
            {/each}
        </div>
    {/if}
</div>
