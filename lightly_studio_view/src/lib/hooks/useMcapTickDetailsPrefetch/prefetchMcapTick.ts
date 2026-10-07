import { getSummaryOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getCameraFrame } from '$lib/api/lightly_studio_local/sdk.gen';
import type { QueryClient } from '@tanstack/svelte-query';
import { getCloudPointFrameOptions } from '$lib/hooks/useCloudPointFrame/useCloudPointFrame.svelte';
import { getTickDetailsOptions } from '$lib/hooks/useTickDetails/useTickDetails';

interface McapTickPrefetchParams {
    datasetId: string;
    sequenceId: string;
    seqNumber: number;
    displayFrameId?: string;
}

/** Prefetches all point-cloud data needed to render one tick. */
export async function prefetchMcapTick(
    client: QueryClient,
    { datasetId, sequenceId, seqNumber, displayFrameId }: McapTickPrefetchParams
): Promise<void> {
    const summary = await client.ensureQueryData(
        getSummaryOptions({ path: { dataset_id: datasetId, sequence_id: sequenceId } })
    );
    const details = await client.ensureQueryData(
        getTickDetailsOptions({ datasetId, sequenceId, seqNumber, displayFrameId })
    );
    const channels = summary.lidar_channels.flatMap((channel) => {
        const locator = details.lidar_channels[channel.group_component_name];
        return locator ? [{ channelId: locator.channel_id, timestampNs: locator.log_time_ns }] : [];
    });
    if (channels.length > 0) {
        await client.prefetchQuery(
            getCloudPointFrameOptions({
                datasetId,
                recordingId: details.recording_id,
                channels,
                displayFrameId
            })
        );
    }

    await Promise.all(
        summary.camera_channels.flatMap((channel) => {
            const frame = details.camera_channels[channel.group_component_name];
            if (!frame || frame.keyframe_log_time_ns === null) return [];
            return [
                getCameraFrame({
                    path: { dataset_id: datasetId, recording_id: details.recording_id },
                    query: {
                        channel_id: channel.channel_id,
                        // Preserve nanosecond precision; the generated client types this query as
                        // number even though the API value is intentionally represented as string.
                        keyframe_timestamp_ns: frame.keyframe_log_time_ns as unknown as number
                    },
                    parseAs: 'arrayBuffer',
                    throwOnError: true
                })
            ];
        })
    );
}
