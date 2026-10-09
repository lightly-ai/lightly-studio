<script lang="ts">
    import CameraProjectionFrame from './CameraProjectionFrame/CameraProjectionFrame.svelte';
    import { useTickDetails } from '$lib/hooks';
    import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';

    /**
     * Horizontal strip of camera tiles for the active point-cloud tick. Each
     * camera channel renders its frame for the current tick, resolved from the
     * tick's per-component MCAP locators keyed by `group_component_name`.
     */
    interface Props {
        /** Dataset the sequence belongs to. */
        datasetId: string;
        /** MCAP sequence being labeled. */
        sequenceId: string;
        /** Zero-based tick position to render frames for. */
        seqNumber: number;
        /** Frame the workspace requests cuboids in, so both share one tick-details query. */
        displayFrameId?: string;
        /** All camera slots configured for the sequence; this is the stable tile layout. */
        cameraChannels: ChannelSummaryView[];
        /** Camera channel IDs currently shown in the projection strip. */
        selectedChannelIds: number[];
    }

    let {
        datasetId,
        sequenceId,
        seqNumber,
        displayFrameId,
        cameraChannels: summaryCameraChannels,
        selectedChannelIds
    }: Props = $props();

    const { tickDetails } = useTickDetails({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getSeqNumber: () => seqNumber,
        getDisplayFrameId: () => displayFrameId || undefined
    });
    const recordingId = $derived(tickDetails.data?.recording_id);
</script>

<div
    class="flex h-full min-h-0 flex-col border-t bg-background p-2"
    data-testid="workspace-projection-strip"
>
    <div class="scrollbar-thin flex min-h-0 flex-1 gap-2 overflow-x-auto">
        {#each summaryCameraChannels.filter( (channel) => selectedChannelIds.includes(channel.channel_id) ) as summaryChannel}
            {@const channel =
                tickDetails.data?.camera_channels[summaryChannel.group_component_name]}
            <CameraProjectionFrame
                {datasetId}
                {recordingId}
                channelId={summaryChannel.channel_id}
                keyframeTimestampNs={channel?.keyframe_log_time_ns ?? undefined}
                logTimeNs={channel?.log_time_ns}
                label={summaryChannel.group_component_name}
            />
        {/each}
    </div>
</div>
