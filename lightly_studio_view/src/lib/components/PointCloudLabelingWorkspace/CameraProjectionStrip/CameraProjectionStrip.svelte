<script lang="ts">
    import CameraProjectionFrame from './CameraProjectionFrame/CameraProjectionFrame.svelte';
    import { useTickDetails } from '$lib/hooks';
    import type { TickChannelView } from '$lib/api/lightly_studio_local/types.gen';

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
        targetFrameId?: string;
    }

    let { datasetId, sequenceId, seqNumber, targetFrameId }: Props = $props();

    const { tickDetails } = useTickDetails({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getSeqNumber: () => seqNumber,
        getTargetFrameId: () => targetFrameId || undefined
    });
    const recordingId = $derived(tickDetails.data?.recording_id);
    const cameraChannels: TickChannelView[] = $derived(
        tickDetails.data?.camera_channels ? Object.values(tickDetails.data.camera_channels) : []
    );
</script>

<div
    class="flex h-full min-h-0 flex-col border-t bg-background p-2"
    data-testid="workspace-projection-strip"
>
    {#if recordingId}
        <div class="scrollbar-thin flex min-h-0 flex-1 gap-2 overflow-x-auto">
            {#each cameraChannels as channel}
                <CameraProjectionFrame
                    {datasetId}
                    {recordingId}
                    channelId={channel.channel_id}
                    timestampNs={channel.keyframe_log_time_ns ?? undefined}
                    label={channel.group_component_name}
                />
            {/each}
        </div>
    {/if}
</div>
