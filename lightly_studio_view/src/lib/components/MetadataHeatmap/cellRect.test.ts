import { describe, expect, it } from 'vitest';
import { rectFromAxisLabel, rectFromCells, selectionFromRect } from './cellRect';

describe('rectFromCells', () => {
    it('orders the corners of a drag in any direction', () => {
        expect(rectFromCells({ x: 3, y: 0 }, { x: 1, y: 2 })).toEqual({
            x0: 1,
            x1: 3,
            y0: 0,
            y1: 2
        });
    });
});

describe('rectFromAxisLabel', () => {
    it('spans the full column of an x label and the full row of a y label', () => {
        const gridSize = { xCount: 4, yCount: 3 };

        expect(rectFromAxisLabel('x', 2, gridSize)).toEqual({ x0: 2, x1: 2, y0: 0, y1: 2 });
        expect(rectFromAxisLabel('y', 1, gridSize)).toEqual({ x0: 0, x1: 3, y0: 1, y1: 1 });
    });
});

describe('selectionFromRect', () => {
    it('lists the bucket indices of both axes', () => {
        expect(selectionFromRect({ x0: 1, x1: 3, y0: 2, y1: 2 })).toEqual({
            x: [1, 2, 3],
            y: [2]
        });
    });
});
