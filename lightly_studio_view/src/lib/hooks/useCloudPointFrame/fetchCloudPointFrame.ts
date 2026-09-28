import { getPointCloud } from '$lib/api/lightly_studio_local';
import { parseCloudPointFrame } from './parseCloudPointFrame';
import type { CloudPointChannelLocator, CloudPointFrame } from './types';

interface FetchCloudPointFrameParams {
    datasetId: string;
    recordingId: string;
    channel: CloudPointChannelLocator;
    signal?: AbortSignal;
}

/** Loads and parses a single point-cloud frame for one channel. */
export async function fetchCloudPointFrame({
    datasetId,
    recordingId,
    channel,
    signal
}: FetchCloudPointFrameParams): Promise<CloudPointFrame> {
    const { channelId, timestampNs } = channel;
    const { data, response } = await getPointCloud({
        path: { dataset_id: datasetId, recording_id: recordingId },
        query: { channel_id: channelId, timestamp_ns: timestampNs },
        parseAs: 'arrayBuffer',
        signal
    });
    if (!response.ok || !data) {
        throw new Error(`Could not load point cloud (${response.status}).`);
    }
    // parseAs: 'arrayBuffer' makes data an ArrayBuffer at runtime, but the type is unknown.
    return parseCloudPointFrame(data as ArrayBuffer, { channelId, timestampNs });
}
