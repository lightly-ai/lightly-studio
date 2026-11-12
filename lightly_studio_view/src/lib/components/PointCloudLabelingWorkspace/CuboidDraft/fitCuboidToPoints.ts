import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { AxisExtent, DraftRectangle } from './cuboidDraft';

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
