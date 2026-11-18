import { describe, expect, it } from 'vitest';
import { getProportionalCuboid } from './orthographicDraft';

const rectangle = { center: [1, 2, 0], size: [2, 4, 6], yaw: 0 } as const;

describe('proportional orthographic cuboid', () => {
    it.each([
        { mode: 'top', center: [1, 2, 1], size: [2, 4, 2] },
        { mode: 'side', center: [1, 2, 0], size: [4, 4, 6] },
        { mode: 'front', center: [1, 2, 0], size: [2, 2, 6] }
    ] as const)('infers the hidden extent in $mode', ({ mode, center, size }) => {
        expect(getProportionalCuboid(mode, rectangle)).toEqual({ center, size, yaw: 0 });
        expect(rectangle.size).toEqual([2, 4, 6]);
    });

    it('rejects a line or click', () => {
        expect(getProportionalCuboid('top', { ...rectangle, size: [2, 0.1, 0.1] })).toBeNull();
    });
});
