import type { PointBatch } from '$lib/components/PointCloudViewer';

/** A parsed point-cloud frame with its batch data, metadata, and source channels. */
export interface CloudPointFrame {
    batch: PointBatch;
    channelId: number;
    timestampNs: string;
    frameId: string;
    sourcePointCount: number;
    bounds: { min: [number, number, number]; max: [number, number, number] } | null;
    channels: Array<{ channelId: number; timestampNs: string; frameId: string }>;
}
