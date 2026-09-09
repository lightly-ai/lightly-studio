import { describe, it, expect } from 'vitest';
import { Box3, Vector3 } from 'three';
import { turboInto } from './colormap';
import { computeActiveBounds, computeCameraPlacement, buildColorBuffer } from './pointCloudUtils';

function turboRgb(value: number): [number, number, number] {
    const out = new Float32Array(3);
    turboInto(value, out, 0);
    return [out[0], out[1], out[2]];
}

describe('turboInto', () => {
    it('clamps input below 0 to the low-end color', () => {
        expect(turboRgb(-1)).toEqual(turboRgb(0));
    });

    it('clamps input above 1 to the high-end color', () => {
        expect(turboRgb(2)).toEqual(turboRgb(1));
    });

    it('returns RGB values in [0, 1]', () => {
        for (const t of [0, 0.25, 0.5, 0.75, 1]) {
            const [r, g, b] = turboRgb(t);
            expect(r).toBeGreaterThanOrEqual(0);
            expect(r).toBeLessThanOrEqual(1);
            expect(g).toBeGreaterThanOrEqual(0);
            expect(g).toBeLessThanOrEqual(1);
            expect(b).toBeGreaterThanOrEqual(0);
            expect(b).toBeLessThanOrEqual(1);
        }
    });

    it('produces distinct colors at different values', () => {
        const [r0, g0, b0] = turboRgb(0);
        const [r1, g1, b1] = turboRgb(1);
        const different =
            Math.abs(r0 - r1) > 0.01 || Math.abs(g0 - g1) > 0.01 || Math.abs(b0 - b1) > 0.01;
        expect(different).toBe(true);
    });
});

describe('buildColorBuffer', () => {
    it('fills with neutral gray in none mode', () => {
        const positions = new Float32Array([1, 2, 3, 4, 5, 6]);
        const intensities = new Float32Array([10, 20]);
        const colors = new Float32Array(6);

        buildColorBuffer(positions, intensities, 2, 'none', colors);

        expect(Array.from(colors)).toEqual([0.5, 0.5, 0.5, 0.5, 0.5, 0.5]);
    });

    it('produces different colors for intensity vs height modes', () => {
        const positions = new Float32Array([0, 0, 0, 1, 2, 6, 2, 4, 3]);
        const intensities = new Float32Array([100, 10, 50]);
        const colorsIntensity = new Float32Array(9);
        const colorsHeight = new Float32Array(9);

        buildColorBuffer(positions, intensities, 3, 'intensity', colorsIntensity);
        buildColorBuffer(positions, intensities, 3, 'height', colorsHeight);

        let different = false;
        for (let i = 0; i < 9; i++) {
            if (Math.abs(colorsIntensity[i] - colorsHeight[i]) > 0.001) {
                different = true;
                break;
            }
        }
        expect(different).toBe(true);
    });

    it('respects a custom intensity range', () => {
        const positions = new Float32Array([0, 0, 0, 1, 1, 1, 2, 2, 2]);
        const intensities = new Float32Array([0, 50, 100]);
        const autoColors = new Float32Array(9);
        const customColors = new Float32Array(9);

        buildColorBuffer(positions, intensities, 3, 'intensity', autoColors);
        buildColorBuffer(positions, intensities, 3, 'intensity', customColors, [0, 200]);

        let different = false;
        for (let i = 0; i < 9; i++) {
            if (Math.abs(autoColors[i] - customColors[i]) > 0.001) {
                different = true;
                break;
            }
        }
        expect(different).toBe(true);
    });
});

describe('computeActiveBounds', () => {
    it('computes bounds from the first count points', () => {
        const positions = new Float32Array([1, 2, 3, 7, 8, 9, 4, 5, 6]);

        const bounds = computeActiveBounds(positions, 3);

        expect(bounds.min).toEqual(new Vector3(1, 2, 3));
        expect(bounds.max).toEqual(new Vector3(7, 8, 9));
    });

    it('ignores data beyond count', () => {
        const positions = new Float32Array([0, 0, 0, 10, 10, 10, 999, 999, 999]);

        const bounds = computeActiveBounds(positions, 2);

        expect(bounds.max).toEqual(new Vector3(10, 10, 10));
    });
});

describe('computeCameraPlacement', () => {
    it('returns default placement for empty box', () => {
        const placement = computeCameraPlacement(new Box3());

        expect(placement.position).toEqual([0, -20, 10]);
        expect(placement.target).toEqual([0, 0, 0]);
    });

    it('computes placement from bounds', () => {
        const bounds = new Box3(new Vector3(0, 0, 0), new Vector3(20, 0, 0));

        const placement = computeCameraPlacement(bounds);

        expect(placement.position).toEqual([40, -30, 19.5]);
        expect(placement.target).toEqual([10, 0, 0]);
    });

    it('keeps the up axis offset shallower than the ground ones', () => {
        // Z is up: a placement dominated by the Z offset would look straight down.
        const bounds = new Box3(new Vector3(0, 0, 0), new Vector3(10, 10, 10));

        const [x, y, z] = computeCameraPlacement(bounds).position;

        expect(Math.abs(z - 5)).toBeLessThan(Math.abs(x - 5));
        expect(Math.abs(z - 5)).toBeLessThan(Math.abs(y - 5));
    });

    it('uses only the provided bounds', () => {
        const bounds = new Box3(new Vector3(0, 0, 0), new Vector3(10, 10, 10));

        const placement = computeCameraPlacement(bounds);

        expect(placement.target).toEqual([5, 5, 5]);
    });
});
