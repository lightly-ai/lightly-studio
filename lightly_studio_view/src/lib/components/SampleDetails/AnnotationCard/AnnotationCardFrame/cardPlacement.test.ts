import { describe, expect, it } from 'vitest';
import { imageRectToScreen, placePanel, rectsIntersect } from './cardPlacement';

const canvas = { left: 0, top: 0, right: 1000, bottom: 600 };
const panel = { width: 200, height: 100 };

describe('placePanel', () => {
    it('places the panel right of the box', () => {
        const box = { left: 100, top: 50, right: 300, bottom: 200 };

        expect(placePanel({ box, canvas, panel })).toEqual({ left: 308, top: 50 });
    });

    it('places the panel left of the box when the right side has no room', () => {
        const box = { left: 700, top: 50, right: 900, bottom: 200 };

        expect(placePanel({ box, canvas, panel })).toEqual({ left: 492, top: 50 });
    });

    it('keeps the panel on the canvas when neither side has room', () => {
        const box = { left: 100, top: 50, right: 900, bottom: 200 };

        expect(placePanel({ box, canvas, panel })).toEqual({ left: 800, top: 50 });
    });

    it('keeps the panel inside the canvas vertically', () => {
        expect(
            placePanel({ box: { left: 100, top: -40, right: 300, bottom: 80 }, canvas, panel }).top
        ).toBe(0);
        expect(
            placePanel({ box: { left: 100, top: 550, right: 300, bottom: 590 }, canvas, panel }).top
        ).toBe(500);
    });
});

describe('imageRectToScreen', () => {
    it('maps an image box through the matrix', () => {
        expect(
            imageRectToScreen({ x: 5, y: 5, width: 10, height: 20 }, { a: 2, d: 2, e: 10, f: 20 })
        ).toEqual({ left: 20, top: 30, right: 40, bottom: 70 });
    });
});

describe('rectsIntersect', () => {
    it('finds a box that is partly on the canvas', () => {
        expect(rectsIntersect({ left: -50, top: 10, right: 10, bottom: 50 }, canvas)).toBe(true);
    });

    it('rejects a box panned off the canvas', () => {
        expect(rectsIntersect({ left: 1100, top: 10, right: 1200, bottom: 50 }, canvas)).toBe(
            false
        );
        expect(rectsIntersect({ left: 10, top: -90, right: 50, bottom: 0 }, canvas)).toBe(false);
    });
});
