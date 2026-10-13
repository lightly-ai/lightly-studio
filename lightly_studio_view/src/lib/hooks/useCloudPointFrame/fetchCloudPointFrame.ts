import { getPointCloud } from '$lib/api/lightly_studio_local';
import { parseCloudPointFrame } from './parseCloudPointFrame';
import type { CloudPointChannelLocator, CloudPointFrame } from './types';

interface FetchCloudPointFrameParams {
    datasetId: string;
    recordingId: string;
    channel: CloudPointChannelLocator;
    /** Frame to express the points in. Omit to keep the sensor frame. */
    displayFrameId?: string;
    signal?: AbortSignal;
}

/** Loads and parses a single point-cloud frame for one channel. */
export async function fetchCloudPointFrame({
    datasetId,
    recordingId,
    channel,
    displayFrameId,
    signal
}: FetchCloudPointFrameParams): Promise<CloudPointFrame> {
    const { channelId, timestampNs } = channel;
    const { data, response } = await getPointCloud({
        path: { dataset_id: datasetId, recording_id: recordingId },
        query: {
            channel_id: channelId,
            timestamp_ns: timestampNs,
            ...(displayFrameId ? { target_frame_id: displayFrameId } : {})
        },
        parseAs: 'arrayBuffer',
        signal
    });
    if (!response.ok || !data || (data as ArrayBuffer).byteLength === 0) {
        throw new Error(`Could not load point cloud (${response.status}).`);
    }
    // parseAs: 'arrayBuffer' makes data an ArrayBuffer at runtime, but the type is unknown.
    return parseCloudPointFrame(data as ArrayBuffer, { channelId, timestampNs });
}
