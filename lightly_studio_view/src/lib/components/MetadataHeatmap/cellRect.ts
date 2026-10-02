import type { HeatmapCell, HeatmapCellRect, HeatmapSelection } from './types';

/** The rectangle spanned by two corner cells, given in any order. */
export const rectFromCells = (first: HeatmapCell, second: HeatmapCell): HeatmapCellRect => ({
    x0: Math.min(first.x, second.x),
    x1: Math.max(first.x, second.x),
    y0: Math.min(first.y, second.y),
    y1: Math.max(first.y, second.y)
});

/** The full column (x label) or the full row (y label) of an axis label. */
export const rectFromAxisLabel = (
    axis: 'x' | 'y',
    index: number,
    { xCount, yCount }: { xCount: number; yCount: number }
): HeatmapCellRect =>
    axis === 'x'
        ? { x0: index, x1: index, y0: 0, y1: yCount - 1 }
        : { x0: 0, x1: xCount - 1, y0: index, y1: index };

/** The bucket indices that a rectangle selects on each axis. */
export const selectionFromRect = (rect: HeatmapCellRect): HeatmapSelection => ({
    x: indexRange(rect.x0, rect.x1),
    y: indexRange(rect.y0, rect.y1)
});

const indexRange = (first: number, last: number): number[] =>
    Array.from({ length: last - first + 1 }, (_, offset) => first + offset);
