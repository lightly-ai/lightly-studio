import type { CameraMode, Vector3 } from '$lib/components/PointCloudLabelingWorkspace/domain';

/** Pointer travel in screen pixels from which a press counts as a drag. */
export const DRAG_THRESHOLD_PX = 4;
/** Smallest allowed size of a cuboid along any axis. */
export const MIN_CUBOID_EXTENT = 0.1;

export interface CuboidBox {
    center: Vector3;
    /** Extent along the box's own X (heading), Y and Z axes. */
    size: Vector3;
    /** Heading: rotation around the vertical axis in radians. */
    yaw: number;
}

export type Axis = 0 | 1 | 2;

export interface DraftRectangle {
    /** Axis not covered by the drag. */
    missingAxis: Axis;
    /** Coordinate of the draft plane on the missing axis. */
    planeCoordinate: number;
    /** Lower and upper corner; both carry planeCoordinate on the missing axis. */
    min: Vector3;
    max: Vector3;
}

/** Ground footprint of an angled draft: one drawn side, widened sideways. */
export interface DraftFootprint {
    /** First point of the drawn side; its Z is the ground height. */
    start: Vector3;
    /** Second point of the drawn side. The heading points from start to end. */
    end: Vector3;
    /** Signed width; positive is to the left of the heading. */
    width: number;
}

export interface AxisExtent {
    min: number;
    max: number;
}

export interface ScreenPoint {
    x: number;
    y: number;
}

export function getMissingAxis(cameraMode: CameraMode): Axis {
    switch (cameraMode) {
        case 'side':
            return 0;
        case 'front':
            return 1;
        case 'top':
        case 'perspective':
            return 2;
    }
}

export function isDrag(start: ScreenPoint, end: ScreenPoint): boolean {
    return Math.hypot(end.x - start.x, end.y - start.y) >= DRAG_THRESHOLD_PX;
}

export function getDraftRectangle(
    cameraMode: CameraMode,
    start: Vector3,
    end: Vector3
): DraftRectangle {
    const missingAxis = getMissingAxis(cameraMode);
    const planeCoordinate = start[missingAxis];
    const min: [number, number, number] = [
        Math.min(start[0], end[0]),
        Math.min(start[1], end[1]),
        Math.min(start[2], end[2])
    ];
    const max: [number, number, number] = [
        Math.max(start[0], end[0]),
        Math.max(start[1], end[1]),
        Math.max(start[2], end[2])
    ];
    min[missingAxis] = planeCoordinate;
    max[missingAxis] = planeCoordinate;
    return { missingAxis, planeCoordinate, min, max };
}

export function getDraftBox(rectangle: DraftRectangle, extent?: AxisExtent): CuboidBox {
    const { missingAxis, planeCoordinate, min, max } = rectangle;
    const low = [...min] as [number, number, number];
    const high = [...max] as [number, number, number];
    if (extent) {
        low[missingAxis] = extent.min;
        high[missingAxis] = extent.max;
    }
    const center: [number, number, number] = [0, 0, 0];
    const size: [number, number, number] = [0, 0, 0];
    for (const axis of [0, 1, 2] as const) {
        center[axis] = (low[axis] + high[axis]) / 2;
        size[axis] = Math.max(high[axis] - low[axis], MIN_CUBOID_EXTENT);
    }
    if (!extent) {
        center[missingAxis] = planeCoordinate;
    }
    return { center, size, yaw: 0 };
}

/** Extent of a footprint raised from the ground to the given world Z. */
export function getHeightExtent(groundZ: number, z: number): AxisExtent {
    return { min: groundZ, max: Math.max(z, groundZ + MIN_CUBOID_EXTENT) };
}

/** Whether the camera mode draws an angled footprint in steps, not one rectangle. */
export function hasAngledFootprint(cameraMode: CameraMode): boolean {
    return cameraMode === 'perspective';
}

/** Heading of the drawn side and its length on the ground. */
export function getFootprintSide(footprint: Pick<DraftFootprint, 'start' | 'end'>) {
    const dx = footprint.end[0] - footprint.start[0];
    const dy = footprint.end[1] - footprint.start[1];
    const length = Math.hypot(dx, dy);
    return { length, yaw: length > 0 ? Math.atan2(dy, dx) : 0 };
}

/** Signed distance of a point from the drawn side; positive is to the left of the heading. */
export function getFootprintWidth(
    footprint: Pick<DraftFootprint, 'start' | 'end'>,
    point: Vector3
): number {
    const { yaw } = getFootprintSide(footprint);
    const dx = point[0] - footprint.start[0];
    const dy = point[1] - footprint.start[1];
    return dy * Math.cos(yaw) - dx * Math.sin(yaw);
}

/** Box over the footprint: flat on the ground, or with the given vertical extent. */
export function getFootprintBox(footprint: DraftFootprint, extent?: AxisExtent): CuboidBox {
    const { start, width } = footprint;
    const { length, yaw } = getFootprintSide(footprint);
    const cos = Math.cos(yaw);
    const sin = Math.sin(yaw);
    const low = extent?.min ?? start[2];
    const high = extent?.max ?? start[2];
    return {
        center: [
            start[0] + (cos * length - sin * width) / 2,
            start[1] + (sin * length + cos * width) / 2,
            (low + high) / 2
        ],
        size: [
            Math.max(length, MIN_CUBOID_EXTENT),
            Math.max(Math.abs(width), MIN_CUBOID_EXTENT),
            Math.max(high - low, MIN_CUBOID_EXTENT)
        ],
        yaw
    };
}
