import { describe, expect, it } from 'vitest';
import { buildJustifiedRows, getJustifiedContentHeight, getVisibleRowRange } from './justifiedRows';

const defaultParams = {
    aspectRatios: [1, 1, 1, 1],
    containerWidth: 300,
    targetRowHeight: 100,
    gap: 10
};

describe('buildJustifiedRows', () => {
    it('fills each row to the container width', () => {
        const rows = buildJustifiedRows(defaultParams);

        // Three squares at 100px plus two 10px gaps is 320 > 300, so the row closes at two.
        expect(rows).toHaveLength(2);
        const [firstRow] = rows;
        const rowWidth =
            firstRow.tiles.reduce((sum, tile) => sum + tile.width, 0) +
            defaultParams.gap * (firstRow.tiles.length - 1);
        expect(rowWidth).toBeCloseTo(defaultParams.containerWidth);
    });

    it('leaves the final row at the target height instead of stretching it', () => {
        const rows = buildJustifiedRows({ ...defaultParams, aspectRatios: [1, 1, 1] });

        expect(rows[rows.length - 1].height).toBe(defaultParams.targetRowHeight);
    });

    it('keeps each item at its own aspect ratio', () => {
        const [row] = buildJustifiedRows({
            ...defaultParams,
            aspectRatios: [2, 0.5],
            containerWidth: 1000
        });

        expect(row.tiles[0].width / row.tiles[0].height).toBeCloseTo(2);
        expect(row.tiles[1].width / row.tiles[1].height).toBeCloseTo(0.5);
    });

    it('keeps one tile per row even when it cannot fit', () => {
        const rows = buildJustifiedRows({
            ...defaultParams,
            aspectRatios: [5, 5],
            containerWidth: 100
        });

        expect(rows).toHaveLength(2);
        expect(rows[0].tiles).toHaveLength(1);
    });

    it('treats a missing or degenerate aspect ratio as square', () => {
        const [row] = buildJustifiedRows({
            ...defaultParams,
            aspectRatios: [Number.NaN],
            containerWidth: 1000
        });

        expect(row.tiles[0].width).toBe(row.tiles[0].height);
    });

    it('returns nothing before the container has been measured', () => {
        expect(buildJustifiedRows({ ...defaultParams, containerWidth: 0 })).toEqual([]);
    });

    it('stacks rows with the gap between them', () => {
        const rows = buildJustifiedRows(defaultParams);

        expect(rows[0].top).toBe(0);
        expect(rows[1].top).toBeCloseTo(rows[0].height + defaultParams.gap);
    });
});

describe('getJustifiedContentHeight', () => {
    it('ends at the last row rather than after a trailing gap', () => {
        const rows = buildJustifiedRows(defaultParams);
        const lastRow = rows[rows.length - 1];

        expect(getJustifiedContentHeight(rows)).toBeCloseTo(lastRow.top + lastRow.height);
    });

    it('is zero with no rows', () => {
        expect(getJustifiedContentHeight([])).toBe(0);
    });
});

describe('getVisibleRowRange', () => {
    const rows = [
        { tiles: [], height: 100, top: 0 },
        { tiles: [], height: 100, top: 110 },
        { tiles: [], height: 100, top: 220 },
        { tiles: [], height: 100, top: 330 }
    ];

    it('covers the rows crossing the viewport', () => {
        expect(
            getVisibleRowRange({ rows, scrollTop: 0, viewportHeight: 150, overscan: 0 })
        ).toEqual({ start: 0, end: 1 });
    });

    it('extends the range by the overscan on both sides', () => {
        expect(
            getVisibleRowRange({ rows, scrollTop: 220, viewportHeight: 100, overscan: 1 })
        ).toEqual({ start: 1, end: 3 });
    });

    it('clamps to the available rows', () => {
        expect(
            getVisibleRowRange({ rows, scrollTop: 10_000, viewportHeight: 100, overscan: 5 })
        ).toEqual({ start: 0, end: 3 });
    });

    it('is empty with no rows', () => {
        expect(
            getVisibleRowRange({ rows: [], scrollTop: 0, viewportHeight: 100, overscan: 3 })
        ).toEqual({ start: 0, end: 0 });
    });
});
