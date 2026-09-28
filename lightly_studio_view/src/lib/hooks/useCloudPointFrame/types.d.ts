import type { PointBatch } from '$lib/components/PointCloudViewer';

/** A 3D vector as an `[x, y, z]` tuple. */
export type Vec3 = [number, number, number];

/** Locates a single point-cloud frame within a channel. */
export interface CloudPointChannelLocator {
    /** Identifier of the channel to load the frame from. */
    channelId: number;
    /** Capture time of the frame, in nanoseconds (string to preserve precision). */
    timestampNs: string;
}

/** Parameters for loading and merging point-cloud frames across channels. */
export interface CloudPointFrameParams {
    /** Identifier of the dataset the recording belongs to. */
    datasetId: string;
    /** Identifier of the recording to load frames from. */
    recordingId: string;
    /** The channels to load and merge into a single frame. */
    channels: CloudPointChannelLocator[];
}

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
    bounds: { min: Vec3; max: Vec3 } | null;
    /** The source channels that were merged into this frame. */
    channels: Array<{ channelId: number; timestampNs: string; frameId: string }>;
}
