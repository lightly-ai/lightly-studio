import type { PointBatch } from '$lib/components/PointCloudViewer';

/** A parsed point-cloud frame with its batch data, metadata, and source channels. */
export interface CloudPointFrame {
    /** The point positions and attributes ready for rendering. */
    batch: PointBatch;
    /** Identifier of the channel this frame belongs to. */
    channelId: number;
    /** Capture time of the frame, in nanoseconds (string to preserve precision). */
    timestampNs: string;
    /** Unique identifier of the frame. */
    frameId: string;
    /** Number of points in the original source before any processing. */
    sourcePointCount: number;
    /** Axis-aligned bounding box of the points, or `null` when unavailable. */
    bounds: { min: [number, number, number]; max: [number, number, number] } | null;
    /** The source channels that were merged into this frame. */
    channels: Array<{ channelId: number; timestampNs: string; frameId: string }>;
}
