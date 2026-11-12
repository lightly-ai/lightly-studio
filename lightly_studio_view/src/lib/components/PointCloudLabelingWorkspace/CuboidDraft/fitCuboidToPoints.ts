import type { PointBatch } from '$lib/components/PointCloudViewer';
import {
    MIN_CUBOID_EXTENT,
    getFootprintSide,
    type AxisExtent,
    type DraftFootprint,
    type DraftRectangle
} from './cuboidDraft';

/** Extent of the missing axis from the points inside the rectangle, or the fallback. */
export function fitMissingAxis(
    rectangle: DraftRectangle,
    batch: PointBatch | undefined
): AxisExtent {
    const { missingAxis, min, max } = rectangle;
    const axisA = missingAxis === 0 ? 1 : 0;
    const axisB = missingAxis === 2 ? 1 : 2;

    let low = Infinity;
    let high = -Infinity;
    for (const { positions, count } of batch ? (batch.segments ?? [batch]) : []) {
        for (let i = 0; i < count; i++) {
            const a = positions[i * 3 + axisA];
            const b = positions[i * 3 + axisB];
            if (a < min[axisA] || a > max[axisA] || b < min[axisB] || b > max[axisB]) {
                continue;
            }
            const value = positions[i * 3 + missingAxis];
            if (value < low) low = value;
            if (value > high) high = value;
        }
    }
    if (low <= high) {
        return { min: low, max: high };
    }
    return getFallbackExtent(rectangle);
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

    let low = Infinity;
    let high = -Infinity;
    for (const { positions, count } of batch ? (batch.segments ?? [batch]) : []) {
        for (let i = 0; i < count; i++) {
            const dx = positions[i * 3] - start[0];
            const dy = positions[i * 3 + 1] - start[1];
            const along = dx * cos + dy * sin;
            const across = dy * cos - dx * sin;
            if (along < 0 || along > length || across < minAcross || across > maxAcross) continue;
            const z = positions[i * 3 + 2];
            if (z < low) low = z;
            if (z > high) high = z;
        }
    }
    if (low <= high) {
        return { min: low, max: high };
    }
    // Without points the box rests on the ground and is as high as its shorter side. The
    // minimum size applies here, so that the box does not grow below the ground later.
    const height = Math.max(Math.min(length, Math.abs(width)), MIN_CUBOID_EXTENT);
    return { min: start[2], max: start[2] + height };
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
