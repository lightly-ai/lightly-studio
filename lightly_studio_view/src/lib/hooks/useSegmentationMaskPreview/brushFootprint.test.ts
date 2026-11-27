import { describe, expect, it } from 'vitest';
import {
    getBrushAnchor,
    getBrushCursor,
    getBrushOutlinePath,
    getBrushSpans,
    getStrokeAnchors,
    getStrokeSpans
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

    it('covers a disc 37 pixels wide and tall for size 37', () => {
        const spans = getBrushSpans({ x: 100, y: 100 }, 37);

        expect(spans).toHaveLength(37);
        expect(spans[0].y).toBe(82);
        expect(spans[36].y).toBe(118);
        expect(spans.find((span) => span.y === 100)).toEqual({ y: 100, xStart: 82, width: 37 });
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

describe('getStrokeSpans', () => {
    it('joins the discs of a size 3 line into one span per row', () => {
        expect(
            getStrokeSpans({
                from: { x: 2, y: 2 },
                to: { x: 6, y: 2 },
                size: 3,
                width: 20,
                height: 20
            })
        ).toEqual([
            { y: 1, xStart: 1, width: 7 },
            { y: 2, xStart: 1, width: 7 },
            { y: 3, xStart: 1, width: 7 }
        ]);
    });

    it('drops the pixels outside the image', () => {
        expect(
            getStrokeSpans({
                from: { x: 0, y: 0 },
                to: { x: 0, y: 0 },
                size: 3,
                width: 20,
                height: 20
            })
        ).toEqual([
            { y: 0, xStart: 0, width: 2 },
            { y: 1, xStart: 0, width: 2 }
        ]);
    });

    it('returns no spans for a stroke fully outside the image', () => {
        expect(
            getStrokeSpans({
                from: { x: -50, y: -50 },
                to: { x: -10, y: 30 },
                size: 5,
                width: 20,
                height: 20
            })
        ).toEqual([]);
    });

    it('keeps two spans in a row when the discs do not meet', () => {
        expect(
            getStrokeSpans({
                from: { x: 2, y: 2 },
                to: { x: 6, y: 6 },
                size: 2,
                width: 20,
                height: 20
            })
        ).toEqual([
            { y: 1, xStart: 1, width: 2 },
            { y: 2, xStart: 1, width: 3 },
            { y: 3, xStart: 2, width: 3 },
            { y: 4, xStart: 3, width: 3 },
            { y: 5, xStart: 4, width: 3 },
            { y: 6, xStart: 5, width: 2 }
        ]);
    });

    it.each([
        { from: { x: 3, y: 4 }, to: { x: 40, y: 17 }, size: 7 },
        { from: { x: 30, y: 2 }, to: { x: 5, y: 45 }, size: 12 },
        { from: { x: -8, y: 20 }, to: { x: 55, y: 28 }, size: 25 },
        { from: { x: 10, y: 10 }, to: { x: 11, y: 38 }, size: 4.6 }
    ])('paints the same pixels as a disc at each anchor ($size px)', ({ from, to, size }) => {
        const width = 50;
        const height = 40;
        const expectedPixels = new Set<string>();
        for (const anchor of getStrokeAnchors(from, to)) {
            for (const span of getBrushSpans(anchor, size)) {
                for (let x = span.xStart; x < span.xStart + span.width; x++) {
                    const isInsideImage = x >= 0 && x < width && span.y >= 0 && span.y < height;
                    if (isInsideImage) expectedPixels.add(`${x},${span.y}`);
                }
            }
        }

        const paintedPixels: string[] = [];
        for (const span of getStrokeSpans({ from, to, size, width, height })) {
            for (let x = span.xStart; x < span.xStart + span.width; x++) {
                paintedPixels.push(`${x},${span.y}`);
            }
        }

        expect(paintedPixels).toHaveLength(expectedPixels.size);
        expect(new Set(paintedPixels)).toEqual(expectedPixels);
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

describe('getBrushCursor', () => {
    it('outlines the exact pixels for a size of 3', () => {
        expect(getBrushCursor({ x: 3.7, y: 5.2 }, 3)).toEqual({
            type: 'outline',
            path: 'M2 4H5V5H5V6H5V7H2V6H2V5H2V4Z'
        });
    });

    it('shows a circle on the nearest pixel corner for an even size above 3', () => {
        expect(getBrushCursor({ x: 10.4, y: 19.6 }, 4)).toEqual({
            type: 'circle',
            center: { x: 10, y: 20 },
            radius: 2
        });
    });

    it('shows a circle on the center of the pixel under the cursor for an odd size above 3', () => {
        expect(getBrushCursor({ x: 3.7, y: 5.2 }, 5)).toEqual({
            type: 'circle',
            center: { x: 3.5, y: 5.5 },
            radius: 2.5
        });
    });
});
