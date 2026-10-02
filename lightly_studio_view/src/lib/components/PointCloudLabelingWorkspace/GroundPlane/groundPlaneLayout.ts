import type { Bounds3, Vector3 } from '$lib/components/PointCloudLabelingWorkspace/domain';

export interface GroundPlaneLayout {
    /** Grid origin in world coordinates, slightly below the lowest point. */
    center: Vector3;
    /** Distance from the cloud center where the infinite grid fades out. */
    fadeDistance: number;
}

const FADE_FACTOR = 0.65;
const Z_OFFSET_FACTOR = 0.001;

/** Returns the grid placement for the given bounds, or null when the footprint is empty. */
export function computeGroundPlaneLayout(bounds: Bounds3): GroundPlaneLayout | null {
    const extentX = bounds.max[0] - bounds.min[0];
    const extentY = bounds.max[1] - bounds.min[1];
    const footprint = Math.max(extentX, extentY);
    if (footprint <= 0) return null;
    return {
        fadeDistance: Math.hypot(extentX, extentY) * FADE_FACTOR,
        center: [
            (bounds.min[0] + bounds.max[0]) / 2,
            (bounds.min[1] + bounds.max[1]) / 2,
            bounds.min[2] - footprint * Z_OFFSET_FACTOR
        ]
    };
}
