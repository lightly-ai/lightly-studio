import type { PointBatch } from '$lib/components/PointCloudViewer/types';

/** A 3D vector as an `[x, y, z]` tuple. */
export type Vec3 = [number, number, number];

/** Parameters for loading a tick and merging the point clouds of its lidar channels. */
export interface CloudPointFrameParams {
    /** Identifier of the dataset the sequence belongs to. */
    datasetId: string;
    /** Identifier of the MCAP sequence that holds the tick. */
    sequenceId: string;
    /** Zero-based tick position in the sequence. */
    seqNumber: number;
    /** Frame to express the points in. Omit to keep each sensor frame. */
    displayFrameId?: string;
    /** Lidar channels to merge. Omit to merge every lidar channel of the tick. */
    selectedChannelIds?: number[];
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
