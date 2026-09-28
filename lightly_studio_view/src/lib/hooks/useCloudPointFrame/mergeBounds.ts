import type { CloudPointFrame, Vec3 } from './types';

/**
 * Merges several per-frame bounding boxes into the single box that encloses all of them.
 *
 * Null entries (frames without bounds) are ignored. For each axis the result takes the
 * smallest `min` and the largest `max` across the available boxes.
 *
 * @param bounds - Per-frame bounds, each either a `{ min, max }` box or `null`.
 * @returns The union box, or `null` when no non-null bounds are provided.
 */
export function mergeBounds(bounds: Array<CloudPointFrame['bounds']>): CloudPointFrame['bounds'] {
    const available = bounds.filter((item) => item !== null);
    if (available.length === 0) return null;
    return {
        min: [0, 1, 2].map((axis) => Math.min(...available.map((item) => item.min[axis]))) as Vec3,
        max: [0, 1, 2].map((axis) => Math.max(...available.map((item) => item.max[axis]))) as Vec3
    };
}
