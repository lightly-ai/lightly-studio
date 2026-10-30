import { describe, expect, it } from 'vitest';
import { createAnnotationFixture } from './fixtures';
import { interpolateCuboidGeometry } from './interpolateCuboidGeometry';

const start = createAnnotationFixture();

describe('interpolateCuboidGeometry', () => {
    it('interpolates position, dimensions, and rotation between authored cuboids', () => {
        const end = {
            ...start,
            center: [14, 2, 3] as const,
            size: [6, 4, 2] as const,
            rotation: [0, 0, 1, 0] as const
        };

        const result = interpolateCuboidGeometry(start, end, 0.5);

        expect(result.center).toEqual([12, 0, 2]);
        expect(result.size).toEqual([5, 3, 2]);
        expect(result.rotation[2]).toBeCloseTo(Math.SQRT1_2);
        expect(result.rotation[3]).toBeCloseTo(Math.SQRT1_2);
    });

    it('takes the shortest quaternion path when endpoints have opposite signs', () => {
        const result = interpolateCuboidGeometry(start, { ...start, rotation: [0, 0, 0, -1] }, 0.5);

        expect(result.rotation).toEqual([0, 0, 0, 1]);
    });

    it('rejects an invalid fraction or incompatible coordinate frame', () => {
        expect(() => interpolateCuboidGeometry(start, start, 1.1)).toThrow(/fraction/);
        expect(() =>
            interpolateCuboidGeometry(
                start,
                { ...start, coordinateFrame: { ...start.coordinateFrame, id: 'other' } },
                0.5
            )
        ).toThrow(/Coordinate frames differ/);
    });
});
