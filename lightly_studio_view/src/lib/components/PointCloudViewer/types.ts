/** Determines how points are colored. */
export type ColorMode = 'none' | 'intensity' | 'height';

/** Camera position and orbit target computed from point cloud bounds. */
export interface CameraPlacement {
    position: [number, number, number];
    target: [number, number, number];
}

/** A batch of points stored in pre-packed typed arrays. */
export interface PointBatch {
    /** Flat position data [x0,y0,z0, x1,y1,z1, ...]. Length >= count * 3. */
    positions: Float32Array;
    /** Per-point intensity values. Length >= count. */
    intensities: Float32Array;
    /** Number of active points in this batch. */
    count: number;
}
