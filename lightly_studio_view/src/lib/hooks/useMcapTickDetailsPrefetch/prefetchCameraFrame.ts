import { getCameraFrame } from '$lib/api/lightly_studio_local/sdk.gen';
import type { ChannelSummaryView, TickChannelView } from '$lib/api/lightly_studio_local/types.gen';

interface PrefetchCameraFrameParams {
    /** Dataset that owns the recording. */
    datasetId: string;
    /** Recording containing the requested camera frame. */
    recordingId: string;
    /** Camera channel configured for the sequence. */
    channel: ChannelSummaryView;
    /** Camera frame locator for the current tick. */
    frame?: TickChannelView;
}

/** Warms the browser cache with the camera frame for one tick and channel. */
export async function prefetchCameraFrame({
    datasetId,
    recordingId,
    channel,
    frame
}: PrefetchCameraFrameParams): Promise<void> {
    if (!frame || frame.keyframe_log_time_ns === null) return;

    await getCameraFrame({
        path: { dataset_id: datasetId, recording_id: recordingId },
        query: {
            channel_id: channel.channel_id,
            // Keep nanosecond precision; the generated client uses number here.
            keyframe_timestamp_ns: frame.keyframe_log_time_ns as unknown as number,
            log_time_ns: frame.log_time_ns as unknown as number
        },
        parseAs: 'arrayBuffer',
        throwOnError: true
    });
}
