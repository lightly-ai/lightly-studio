import type { Box3, BufferGeometry } from 'three';
import type { ColorMode, PointHighlight } from './pointCloudUtils';

/** A batch of points stored in pre-packed typed arrays. */
export interface PointBatch {
    /** Flat position data [x0,y0,z0, x1,y1,z1, ...]. Length >= count * 3. */
    positions: Float32Array;
    /** Per-point intensity values. Length >= count. */
    intensities: Float32Array;
    /** Optional packed linear RGB values [r0,g0,b0,...]. Length >= count * 3. */
    colors?: Float32Array;
    /** Number of active points in this batch. */
    count: number;
}

/** Manages the Three.js geometry backing a rendered point cloud. */
export interface PointCloudBuffer {
    /** The Three.js geometry holding the point positions and colors. */
    geometry: BufferGeometry;
    /** Uploads a batch of point positions and returns their bounding box. */
    updatePositions: (batch: PointBatch) => Box3 | undefined;
    /** Recomputes per-point colors for the given color mode. */
    updateColors: (
        count: number,
        colorMode: ColorMode,
        intensityRange?: [number, number],
        pointColors?: Float32Array,
        highlight?: PointHighlight
    ) => void;
    /** Releases the underlying GPU resources. */
    dispose: () => void;
}
