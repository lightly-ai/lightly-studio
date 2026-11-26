import { describe, expect, it } from 'vitest';
import {
    getBrushAnchor,
    getBrushOutlinePath,
    getBrushSpans,
    getStrokeAnchors
} from './brushFootprint';

describe('getBrushAnchor', () => {
    it('uses the pixel under the cursor for an odd size', () => {
        expect(getBrushAnchor({ x: 3.7, y: 5.2 }, 3)).toEqual({ x: 3, y: 5 });
    });

    it('uses the nearest pixel corner for an even size', () => {
        expect(getBrushAnchor({ x: 3.7, y: 5.2 }, 2)).toEqual({ x: 4, y: 5 });
    });

    it('rounds a fractional size before it picks the center', () => {
        expect(getBrushAnchor({ x: 3.7, y: 5.2 }, 2.6)).toEqual({ x: 3, y: 5 });
    });
});

describe('getBrushSpans', () => {
    it('covers exactly one pixel for size 1', () => {
        expect(getBrushSpans({ x: 3, y: 5 }, 1)).toEqual([{ y: 5, xStart: 3, width: 1 }]);
    });

    it('covers exactly 2x2 pixels around the corner for size 2', () => {
        expect(getBrushSpans({ x: 4, y: 5 }, 2)).toEqual([
            { y: 4, xStart: 3, width: 2 },
            { y: 5, xStart: 3, width: 2 }
        ]);
    });

    it('covers a full 3x3 square for size 3', () => {
        expect(getBrushSpans({ x: 10, y: 20 }, 3)).toEqual([
            { y: 19, xStart: 9, width: 3 },
            { y: 20, xStart: 9, width: 3 },
            { y: 21, xStart: 9, width: 3 }
        ]);
    });

    it('cuts the corners of a 4x4 square for size 4', () => {
        expect(getBrushSpans({ x: 10, y: 20 }, 4)).toEqual([
            { y: 18, xStart: 9, width: 2 },
            { y: 19, xStart: 8, width: 4 },
            { y: 20, xStart: 8, width: 4 },
            { y: 21, xStart: 9, width: 2 }
        ]);
    });

    it('rounds a fractional size to whole pixels', () => {
        expect(getBrushSpans({ x: 3, y: 5 }, 2.5)).toEqual([
            { y: 4, xStart: 2, width: 3 },
            { y: 5, xStart: 2, width: 3 },
            { y: 6, xStart: 2, width: 3 }
        ]);
    });

    it('paints one pixel for a size below 1', () => {
        expect(getBrushSpans({ x: 3, y: 5 }, 0.4)).toEqual([{ y: 5, xStart: 3, width: 1 }]);
    });
});

describe('getStrokeAnchors', () => {
    it('returns one point when both ends are the same', () => {
        expect(getStrokeAnchors({ x: 2, y: 3 }, { x: 2, y: 3 })).toEqual([{ x: 2, y: 3 }]);
    });

    it('returns every pixel step of a shallow line', () => {
        expect(getStrokeAnchors({ x: 0, y: 0 }, { x: 5, y: 2 })).toEqual([
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 2, y: 1 },
            { x: 3, y: 1 },
            { x: 4, y: 2 },
            { x: 5, y: 2 }
        ]);
    });

    it('returns every pixel step of a vertical line going up', () => {
        expect(getStrokeAnchors({ x: 1, y: 3 }, { x: 1, y: 0 })).toEqual([
            { x: 1, y: 3 },
            { x: 1, y: 2 },
            { x: 1, y: 1 },
            { x: 1, y: 0 }
        ]);
    });

    it('returns every pixel step of a diagonal line', () => {
        expect(getStrokeAnchors({ x: 0, y: 2 }, { x: 2, y: 0 })).toEqual([
            { x: 0, y: 2 },
            { x: 1, y: 1 },
            { x: 2, y: 0 }
        ]);
    });
});

describe('getBrushOutlinePath', () => {
    it('outlines the single pixel of size 1', () => {
        expect(getBrushOutlinePath({ x: 3.7, y: 5.2 }, 1)).toBe('M3 5H4V6H3V5Z');
    });

    it('outlines the staircase of a size 4 disc', () => {
        expect(getBrushOutlinePath({ x: 10.4, y: 19.6 }, 4)).toBe(
            'M9 18H11V19H12V20H12V21H11V22H9V21H8V20H8V19H9V18Z'
        );
    });
});
