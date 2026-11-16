import type { PointBatch } from '$lib/components/PointCloudViewer';
import {
    MIN_CUBOID_EXTENT,
    getFootprintSide,
    type Axis,
    type AxisExtent,
    type DraftFootprint,
    type DraftRectangle
} from './cuboidDraft';

type PointTest = (x: number, y: number, z: number) => boolean;

/** Extent of the missing axis from the points inside the rectangle, or the fallback. */
export function fitMissingAxis(
    rectangle: DraftRectangle,
    batch: PointBatch | undefined
): AxisExtent {
    const { missingAxis, min, max } = rectangle;
    const axisA = missingAxis === 0 ? 1 : 0;
    const axisB = missingAxis === 2 ? 1 : 2;
    const isWithin = (value: number, axis: Axis) => value >= min[axis] && value <= max[axis];
    const isInside: PointTest = (...point) =>
        isWithin(point[axisA], axisA) && isWithin(point[axisB], axisB);
    return getAxisRange(batch, missingAxis, isInside) ?? getFallbackExtent(rectangle);
}

/** Vertical extent of the points inside an angled footprint, or the fallback. */
export function fitFootprintHeight(
    footprint: DraftFootprint,
    batch: PointBatch | undefined
): AxisExtent {
    const { start, width } = footprint;
    const { length, yaw } = getFootprintSide(footprint);
    const cos = Math.cos(yaw);
    const sin = Math.sin(yaw);
    const minAcross = Math.min(0, width);
    const maxAcross = Math.max(0, width);
    const isInside: PointTest = (x, y) => {
        const along = (x - start[0]) * cos + (y - start[1]) * sin;
        const across = (y - start[1]) * cos - (x - start[0]) * sin;
        return along >= 0 && along <= length && across >= minAcross && across <= maxAcross;
    };
    const range = getAxisRange(batch, 2, isInside);
    if (range) return range;
    // Without points the box rests on the ground and is as high as its shorter side. The
    // minimum size applies here, so that the box does not grow below the ground later.
    const height = Math.max(Math.min(length, Math.abs(width)), MIN_CUBOID_EXTENT);
    return { min: start[2], max: start[2] + height };
}

/** Lowest and highest coordinate on the axis of the points that pass the test; null without one. */
function getAxisRange(
    batch: PointBatch | undefined,
    axis: Axis,
    isInside: PointTest
): AxisExtent | null {
    let low = Infinity;
    let high = -Infinity;
    for (const { positions, count } of getSegments(batch)) {
        for (let offset = 0; offset < count * 3; offset += 3) {
            if (!isInside(positions[offset], positions[offset + 1], positions[offset + 2])) {
                continue;
            }
            low = Math.min(low, positions[offset + axis]);
            high = Math.max(high, positions[offset + axis]);
        }
    }
    return low <= high ? { min: low, max: high } : null;
}

function getSegments(batch: PointBatch | undefined): readonly PointBatch[] {
    if (!batch) return [];
    return batch.segments ?? [batch];
}

function getFallbackExtent(rectangle: DraftRectangle): AxisExtent {
    const { missingAxis, planeCoordinate, min, max } = rectangle;
    const sides = ([0, 1, 2] as const)
        .filter((axis) => axis !== missingAxis)
        .map((axis) => max[axis] - min[axis]);
    const shorterSide = Math.min(...sides);
    if (missingAxis === 2) {
        return { min: planeCoordinate, max: planeCoordinate + shorterSide };
    }
    return {
        min: planeCoordinate - shorterSide / 2,
        max: planeCoordinate + shorterSide / 2
    };
}
