import { client } from '$lib/api/lightly_studio_local/client.gen';

interface CameraFrameUrlParams {
    datasetId: string;
    recordingId: string;
    channelId: number;
    /** Nanosecond log time of the keyframe to decode from, kept as a string to preserve full precision. */
    keyframeTimestampNs: string;
    /** Nanosecond log time of the frame to show, kept as a string to preserve full precision. */
    logTimeNs: string;
}

/**
 * Builds the camera-frame endpoint URL for use as an `<img src>`.
 *
 * Uses the generated API client's configured base URL and route template so the
 * URL stays in sync with the rest of the SDK instead of hardcoding the host.
 */
export function getCameraFrameUrl({
    datasetId,
    recordingId,
    channelId,
    keyframeTimestampNs,
    logTimeNs
}: CameraFrameUrlParams): string {
    return client.buildUrl({
        url: '/datasets/{dataset_id}/recordings/{recording_id}/camera-frame',
        baseUrl: client.getConfig().baseUrl,
        path: { dataset_id: datasetId, recording_id: recordingId },
        query: {
            channel_id: channelId,
            keyframe_timestamp_ns: keyframeTimestampNs,
            log_time_ns: logTimeNs
        }
    });
}
