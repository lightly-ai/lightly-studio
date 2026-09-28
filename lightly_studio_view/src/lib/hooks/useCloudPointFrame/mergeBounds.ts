import type { CloudPointFrame } from './types';

type Bounds = NonNullable<CloudPointFrame['bounds']>;

/** Reduces one axis across the available boxes, e.g. the smallest `min` or largest `max`. */
function axisExtrema(
    boxes: Bounds[],
    edge: 'min' | 'max',
    reduce: (a: number, b: number) => number
): Bounds['min'] {
    return [0, 1, 2].map((axis) =>
        boxes.reduce((acc, box) => reduce(acc, box[edge][axis]), boxes[0][edge][axis])
    ) as Bounds['min'];
}

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
        min: axisExtrema(available, 'min', Math.min),
        max: axisExtrema(available, 'max', Math.max)
    };
}
