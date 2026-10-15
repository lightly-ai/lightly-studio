import { describe, expect, it } from 'vitest';

import { getAxisLinePositions } from './axisLinePositions';

// Pixels = data * 10 + offset. The y axis points up in data space and down in pixels.
const createProxy = (offsetX: number, offsetY: number) => ({
    location: (x: number, y: number) => ({ x: x * 10 + offsetX, y: -y * 10 + offsetY }),
    width: 400,
    height: 300
});

describe('getAxisLinePositions', () => {
    it('returns the pixel position of the origin when it is in view', () => {
        expect(getAxisLinePositions(createProxy(120, 80))).toEqual({ x: 120, y: 80 });
    });

    it('returns null for a line that is outside the plot', () => {
        expect(getAxisLinePositions(createProxy(-1, 80))).toEqual({ x: null, y: 80 });
        expect(getAxisLinePositions(createProxy(401, 80))).toEqual({ x: null, y: 80 });
        expect(getAxisLinePositions(createProxy(120, -1))).toEqual({ x: 120, y: null });
        expect(getAxisLinePositions(createProxy(120, 301))).toEqual({ x: 120, y: null });
    });
});
