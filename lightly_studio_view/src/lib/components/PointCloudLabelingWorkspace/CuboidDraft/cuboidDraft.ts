import type {
    Bounds3,
    CameraMode,
    Vector3
} from '$lib/components/PointCloudLabelingWorkspace/domain';

/** Pointer travel in screen pixels from which a press counts as a drag. */
export const DRAG_THRESHOLD_PX = 4;
/** Smallest allowed size of a cuboid along any axis. */
export const MIN_CUBOID_EXTENT = 0.1;

const DEFAULT_CUBOID_DIAGONAL_RATIO = 0.02;

export interface CuboidBox {
    center: Vector3;
    size: Vector3;
}

export type CuboidPlacement = { kind: 'drop'; position: Vector3 } | { kind: 'box'; box: CuboidBox };

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
    return { center, size };
}

export function getDefaultCuboidBox(position: Vector3, bounds: Bounds3): CuboidBox {
    const diagonal = Math.hypot(
        bounds.max[0] - bounds.min[0],
        bounds.max[1] - bounds.min[1],
        bounds.max[2] - bounds.min[2]
    );
    const edge = Math.max(diagonal * DEFAULT_CUBOID_DIAGONAL_RATIO, MIN_CUBOID_EXTENT);
    return {
        center: [position[0], position[1], position[2] + edge / 2],
        size: [edge, edge, edge]
    };
}
