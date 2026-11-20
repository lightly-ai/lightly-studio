import type { PointBatch } from '$lib/components/PointCloudViewer';
import {
    MIN_CUBOID_EXTENT,
    getFootprintBox,
    getFootprintSide,
    type Axis,
    type AxisExtent,
    type DraftFootprint,
    type DraftRectangle
} from './cuboidDraft';
import { forEachPoint } from './forEachPoint';

type PointTest = (x: number, y: number, z: number) => boolean;

/** Points below this height above the ground are ground returns. */
const GROUND_CLEARANCE = 0.15;
/** Vertical gap that separates the object from clutter above it. */
const MAX_VERTICAL_GAP = 0.5;
/** An object with its lowest point this close to the ground rests on the ground. */
const GROUND_CONTACT_DISTANCE = 0.5;
/** Ground search margin around a footprint. */
const GROUND_SEARCH_MARGIN = 1;
/** Fewest points in a thin layer that make it the ground. */
const MIN_GROUND_POINTS = 10;

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

/**
 * Vertical extent of the object in the footprint, without ground returns and clutter above a
 * vertical gap; a fallback height without points.
 */
export function fitFootprintHeight(
    footprint: DraftFootprint,
    groundZ: number,
    batch: PointBatch | undefined
): AxisExtent {
    const isInFootprint = createFootprintTest(footprint);
    const heights: number[] = [];
    forEachPoint(batch, (x, y, z) => {
        if (z > groundZ + GROUND_CLEARANCE && isInFootprint(x, y, z)) heights.push(z);
    });
    if (heights.length > 0) return getObjectExtent(heights, groundZ);
    // Without points the box rests on the ground and is as high as its shorter side. The
    // minimum size applies here, so that the box does not grow below the ground later.
    const { length } = getFootprintSide(footprint);
    const height = Math.max(Math.min(length, Math.abs(footprint.width)), MIN_CUBOID_EXTENT);
    return { min: groundZ, max: groundZ + height };
}

/** Ground height under and around the footprint, or null. */
export function estimateFootprintGround(
    footprint: DraftFootprint,
    batch: PointBatch | undefined
): number | null {
    const { center } = getFootprintBox(footprint);
    const { length } = getFootprintSide(footprint);
    const radius = Math.hypot(length, footprint.width) / 2 + GROUND_SEARCH_MARGIN;
    return estimateGroundHeight(batch, center[0], center[1], radius);
}

/** Height of the lowest thin layer of points within the radius, or null. Noise forms no layer. */
export function estimateGroundHeight(
    batch: PointBatch | undefined,
    x: number,
    y: number,
    radius: number
): number | null {
    const radiusSquared = radius ** 2;
    const heights: number[] = [];
    forEachPoint(batch, (pointX, pointY, pointZ) => {
        const offsetX = pointX - x;
        if (Math.abs(offsetX) > radius) return;
        const offsetY = pointY - y;
        if (offsetX ** 2 + offsetY ** 2 <= radiusSquared) heights.push(pointZ);
    });
    heights.sort((a, b) => a - b);
    for (let low = 0; low + MIN_GROUND_POINTS <= heights.length; low++) {
        const layerTop = heights[low + MIN_GROUND_POINTS - 1];
        if (layerTop - heights[low] <= GROUND_CLEARANCE) return heights[low];
    }
    return null;
}

function createFootprintTest(footprint: DraftFootprint): PointTest {
    const { start, width } = footprint;
    const { length, yaw } = getFootprintSide(footprint);
    const cos = Math.cos(yaw);
    const sin = Math.sin(yaw);
    const minAcross = Math.min(0, width);
    const maxAcross = Math.max(0, width);
    return (x, y) => {
        const along = (x - start[0]) * cos + (y - start[1]) * sin;
        const across = (y - start[1]) * cos - (x - start[0]) * sin;
        return along >= 0 && along <= length && across >= minAcross && across <= maxAcross;
    };
}

/** Extent from the lowest height to the first large gap, from the ground when near it. */
function getObjectExtent(heights: number[], groundZ: number): AxisExtent {
    heights.sort((a, b) => a - b);
    const lowest = heights[0];
    let highest = lowest;
    for (const height of heights) {
        if (height - highest > MAX_VERTICAL_GAP) break;
        highest = height;
    }
    const standsOnGround = lowest - groundZ <= GROUND_CONTACT_DISTANCE;
    return { min: standsOnGround ? groundZ : lowest, max: highest };
}

/** Lowest and highest coordinate on the axis of the points that pass the test; null without one. */
function getAxisRange(
    batch: PointBatch | undefined,
    axis: Axis,
    isInside: PointTest
): AxisExtent | null {
    let low = Infinity;
    let high = -Infinity;
    forEachPoint(batch, (...point) => {
        if (!isInside(...point)) return;
        low = Math.min(low, point[axis]);
        high = Math.max(high, point[axis]);
    });
    return low <= high ? { min: low, max: high } : null;
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
