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
    }

    let { datasetId, sequenceId, seqNumber }: Props = $props();

    const { tickDetails } = useTickDetails({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getSeqNumber: () => seqNumber
    });
    const recordingId = $derived(tickDetails.data?.recording_id);
    const cameraChannels: TickChannelView[] = $derived(
        tickDetails.data?.channels ? Object.values(tickDetails.data?.channels) : []
    );
</script>

<div
    class="flex h-full min-h-0 flex-col border-t bg-background"
    data-testid="workspace-projection-strip"
>
    <div class="flex shrink-0 items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground">
        <span class="font-medium text-foreground">Cameras</span>
    </div>
    {#if recordingId}
        <div class="flex min-h-0 flex-1 gap-2 overflow-x-auto px-3 pb-2">
            {#each cameraChannels as channel}
                {#if channel.keyframe_log_time_ns}
                    <CameraProjectionFrame
                        {datasetId}
                        {recordingId}
                        channelId={channel.channel_id}
                        timestampNs={channel.keyframe_log_time_ns}
                        label={channel.group_component_name}
                    />
                {/if}
            {/each}
        </div>
    {/if}
</div>
