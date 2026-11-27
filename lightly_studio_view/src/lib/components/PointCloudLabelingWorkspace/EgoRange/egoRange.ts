import type { Vector3 } from '../domain';

/** The range around the ego, in the frame the scene is shown in. */
export interface EgoRange {
    /** Origin of the ego frame, in meters. */
    readonly position: Vector3;
    /** Radius of the range in the ground plane, in meters. */
    readonly radius: number;
}

/** Distance in the x-y plane, in meters. The height difference is ignored. */
export function getFlatDistance(point: Vector3, egoPosition: Vector3): number {
    return Math.hypot(point[0] - egoPosition[0], point[1] - egoPosition[1]);
}

export function isBeyondRange(distance: number, radius: number): boolean {
    return distance > radius;
}

export function formatDistance(meters: number): string {
    return `${meters.toFixed(1)} m`;
}
