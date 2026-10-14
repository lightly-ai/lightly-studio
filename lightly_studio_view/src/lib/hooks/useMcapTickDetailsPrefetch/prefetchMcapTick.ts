import { getSummaryOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { QueryClient } from '@tanstack/svelte-query';
import { getCloudPointFrameOptions } from '$lib/hooks/useCloudPointFrame/getCloudPointFrameOptions';
import { getTickDetailsOptions } from '$lib/hooks/useTickDetails/getTickDetailsOptions';
import { prefetchCameraFrame } from './prefetchCameraFrame';

interface McapTickPrefetchParams {
    /** Dataset that owns the sequence. */
    datasetId: string;
    /** Sequence whose tick should be prefetched. */
    sequenceId: string;
    /** Zero-based tick position in the sequence. */
    seqNumber: number;
    /** Optional target frame for transforming annotations. */
    displayFrameId?: string;
}

/** Prefetches the cached data needed to render one MCAP tick. */
export async function prefetchMcapTick(
    /** Query client that owns the visible workspace cache. */
    client: QueryClient,
    { datasetId, sequenceId, seqNumber, displayFrameId }: McapTickPrefetchParams
): Promise<void> {
    const [summary, details] = await Promise.all([
        client.ensureQueryData(
            getSummaryOptions({ path: { dataset_id: datasetId, sequence_id: sequenceId } })
        ),
        client.ensureQueryData(
            getTickDetailsOptions({ datasetId, sequenceId, seqNumber, displayFrameId })
        )
    ]);

    const channels = summary.lidar_channels.flatMap((channel) => {
        const locator = details.lidar_channels[channel.group_component_name];
        return locator ? [{ channelId: locator.channel_id, timestampNs: locator.log_time_ns }] : [];
    });
    const cloudPointPromise =
        channels.length === 0
            ? Promise.resolve()
            : client.ensureQueryData(
                  getCloudPointFrameOptions({
                      datasetId,
                      recordingId: details.recording_id,
                      channels,
                      displayFrameId
                  })
              );
    const cameraPromise = Promise.all(
        summary.camera_channels.map((channel) =>
            prefetchCameraFrame({
                datasetId,
                recordingId: details.recording_id,
                channel,
                frame: details.camera_channels[channel.group_component_name]
            })
        )
    );

    await Promise.all([cloudPointPromise, cameraPromise]);
}
