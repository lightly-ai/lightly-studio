import { getTickData } from '$lib/api/lightly_studio_local';
import { parseCloudPointFrame } from '$lib/hooks/useCloudPointFrame/parseCloudPointFrame';
import type { CloudPointFrame } from '$lib/hooks/useCloudPointFrame/types';
import { decodeTickPayloads, TickPayloadKind } from './decodeTickPayloads';

export interface TickDataParams {
    /** Dataset the sequence belongs to. */
    datasetId: string;
    /** MCAP sequence that holds the tick. */
    sequenceId: string;
    /** Zero-based tick position in the sequence. */
    seqNumber: number;
    /** Frame to express the points in. Omit to keep each sensor frame. */
    displayFrameId?: string;
    /** Height of the camera images in pixels. */
    cameraHeight: number;
}

/** The decoded sensor data of one tick. */
export interface TickData {
    /** One parsed point cloud per lidar channel. */
    pointClouds: CloudPointFrame[];
    /** One JPEG image per camera channel, keyed by channel id. */
    cameraFrames: Record<number, Blob>;
}

/** Loads the point clouds and camera frames of one tick with one request. */
export async function fetchTickData(
    { datasetId, sequenceId, seqNumber, displayFrameId, cameraHeight }: TickDataParams,
    signal?: AbortSignal
): Promise<TickData> {
    const { data, response } = await getTickData({
        path: { dataset_id: datasetId, sequence_id: sequenceId, seq_number: seqNumber },
        query: {
            camera_height: cameraHeight,
            ...(displayFrameId ? { target_frame_id: displayFrameId } : {})
        },
        parseAs: 'arrayBuffer',
        signal
    });
    if (!response.ok || !data) {
        throw new Error(`Could not load tick ${seqNumber} (${response.status}).`);
    }
    // parseAs: 'arrayBuffer' makes data an ArrayBuffer at runtime, but the type is unknown.
    const payloads = decodeTickPayloads(data as ArrayBuffer);
    const pointClouds = await Promise.all(
        payloads
            .filter((payload) => payload.kind === TickPayloadKind.POINT_CLOUD)
            .map(({ bytes, channelId, logTimeNs }) =>
                parseCloudPointFrame(bytes, { channelId, timestampNs: logTimeNs })
            )
    );
    const cameraFrames: Record<number, Blob> = {};
    for (const payload of payloads) {
        if (payload.kind !== TickPayloadKind.CAMERA_JPEG) continue;
        cameraFrames[payload.channelId] = new Blob([payload.bytes], { type: 'image/jpeg' });
    }
    return { pointClouds, cameraFrames };
}
