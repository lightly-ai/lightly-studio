import { describe, expect, it } from 'vitest';
import type { BufferAttribute } from 'three';
import { createPointCloudBuffer } from './pointCloudBuffer';

describe('createPointCloudBuffer', () => {
    it('copies active points and computes their bounds', () => {
        const buffer = createPointCloudBuffer();

        const bounds = buffer.updatePositions({
            positions: new Float32Array([1, 2, 3, 4, 5, 6, 99, 99, 99]),
            intensities: new Float32Array([10, 20, 30]),
            count: 2
        });

        expect(buffer.geometry.drawRange).toMatchObject({ start: 0, count: 2 });
        expect(
            Array.from((buffer.geometry.getAttribute('position') as BufferAttribute).array)
        ).toEqual([1, 2, 3, 4, 5, 6]);
        expect(bounds?.min.toArray()).toEqual([1, 2, 3]);
        expect(bounds?.max.toArray()).toEqual([4, 5, 6]);

        buffer.dispose();
    });

    it('updates colors from the copied intensity and position data', () => {
        const buffer = createPointCloudBuffer();
        buffer.updatePositions({
            positions: new Float32Array([1, 2, 3, 4, 5, 6]),
            intensities: new Float32Array([10, 20]),
            count: 2
        });

        buffer.updateColors(2, 'none');

        expect(
            Array.from((buffer.geometry.getAttribute('color') as BufferAttribute).array)
        ).toEqual([0.5, 0.5, 0.5, 0.5, 0.5, 0.5]);

        buffer.dispose();
    });
});
