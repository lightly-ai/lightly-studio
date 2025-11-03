import { describe, it, expect } from 'vitest';
import { isPointInPolygon } from './isPointInPolygon';

describe('isPointInPolygon', () => {
    it('returns true for point inside a simple square', () => {
        const polygon = [
            { x: 0, y: 0 },
            { x: 10, y: 0 },
            { x: 10, y: 10 },
            { x: 0, y: 10 }
        ];

        expect(isPointInPolygon(5, 5, polygon)).toBe(true);
    });

    it('returns false for point outside a simple square', () => {
        const polygon = [
            { x: 0, y: 0 },
            { x: 10, y: 0 },
            { x: 10, y: 10 },
            { x: 0, y: 10 }
        ];

        expect(isPointInPolygon(15, 15, polygon)).toBe(false);
    });

    it('returns false for point on the left of the square', () => {
        const polygon = [
            { x: 0, y: 0 },
            { x: 10, y: 0 },
            { x: 10, y: 10 },
            { x: 0, y: 10 }
        ];

        expect(isPointInPolygon(-5, 5, polygon)).toBe(false);
    });

    it('returns true for point on the edge of polygon', () => {
        const polygon = [
            { x: 0, y: 0 },
            { x: 10, y: 0 },
            { x: 10, y: 10 },
            { x: 0, y: 10 }
        ];

        expect(isPointInPolygon(0, 5, polygon)).toBe(true);
    });

    it('returns true for point inside a triangle', () => {
        const polygon = [
            { x: 0, y: 0 },
            { x: 10, y: 0 },
            { x: 5, y: 10 }
        ];

        expect(isPointInPolygon(5, 3, polygon)).toBe(true);
    });

    it('returns false for point outside a triangle', () => {
        const polygon = [
            { x: 0, y: 0 },
            { x: 10, y: 0 },
            { x: 5, y: 10 }
        ];

        expect(isPointInPolygon(1, 8, polygon)).toBe(false);
    });

    it('returns true for point inside a complex polygon', () => {
        const polygon = [
            { x: 0, y: 0 },
            { x: 20, y: 0 },
            { x: 20, y: 10 },
            { x: 10, y: 10 },
            { x: 10, y: 20 },
            { x: 0, y: 20 }
        ];

        expect(isPointInPolygon(5, 5, polygon)).toBe(true);
        expect(isPointInPolygon(15, 5, polygon)).toBe(true);
        expect(isPointInPolygon(5, 15, polygon)).toBe(true);
    });

    it('returns false for point in the concave part of complex polygon', () => {
        const polygon = [
            { x: 0, y: 0 },
            { x: 20, y: 0 },
            { x: 20, y: 10 },
            { x: 10, y: 10 },
            { x: 10, y: 20 },
            { x: 0, y: 20 }
        ];

        expect(isPointInPolygon(15, 15, polygon)).toBe(false);
    });

    it('handles polygon with negative coordinates', () => {
        const polygon = [
            { x: -10, y: -10 },
            { x: 10, y: -10 },
            { x: 10, y: 10 },
            { x: -10, y: 10 }
        ];

        expect(isPointInPolygon(0, 0, polygon)).toBe(true);
        expect(isPointInPolygon(-5, -5, polygon)).toBe(true);
        expect(isPointInPolygon(15, 15, polygon)).toBe(false);
    });

    it('handles floating point coordinates', () => {
        const polygon = [
            { x: 0.5, y: 0.5 },
            { x: 10.5, y: 0.5 },
            { x: 10.5, y: 10.5 },
            { x: 0.5, y: 10.5 }
        ];

        expect(isPointInPolygon(5.25, 5.75, polygon)).toBe(true);
        expect(isPointInPolygon(0.25, 0.25, polygon)).toBe(false);
    });

    it('handles horizontal edge case', () => {
        const polygon = [
            { x: 0, y: 5 },
            { x: 10, y: 5 },
            { x: 10, y: 15 },
            { x: 0, y: 15 }
        ];

        expect(isPointInPolygon(5, 10, polygon)).toBe(true);
    });

    it('handles vertical edge parallel case', () => {
        const polygon = [
            { x: 5, y: 0 },
            { x: 15, y: 0 },
            { x: 15, y: 10 },
            { x: 5, y: 10 }
        ];

        expect(isPointInPolygon(10, 5, polygon)).toBe(true);
        expect(isPointInPolygon(2, 5, polygon)).toBe(false);
    });

    it('handles empty polygon', () => {
        expect(isPointInPolygon(5, 5, [])).toBe(false);
    });

    it('handles single point polygon', () => {
        const polygon = [{ x: 5, y: 5 }];

        expect(isPointInPolygon(5, 5, polygon)).toBe(false);
    });

    it('handles two point polygon', () => {
        const polygon = [
            { x: 0, y: 0 },
            { x: 10, y: 10 }
        ];

        expect(isPointInPolygon(5, 5, polygon)).toBe(false);
    });

    it('handles pentagon shape', () => {
        const polygon = [
            { x: 5, y: 0 },
            { x: 10, y: 3 },
            { x: 8, y: 9 },
            { x: 2, y: 9 },
            { x: 0, y: 3 }
        ];

        expect(isPointInPolygon(5, 5, polygon)).toBe(true);
        expect(isPointInPolygon(11, 5, polygon)).toBe(false);
    });
});
