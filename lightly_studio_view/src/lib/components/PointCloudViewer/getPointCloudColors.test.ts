import { describe, expect, it } from 'vitest';
import { getPointCloudColors } from './getPointCloudColors';
import { buildColorBuffer } from './pointCloudUtils';

const batch = {
    positions: new Float32Array([0, 0, 0, 1, 2, 3]),
    intensities: new Float32Array([10, 20]),
    count: 2
};

describe('shared point cloud colors', () => {
    it('reuses the mapped colors across views and updates them when the mode or range changes', () => {
        const first = getPointCloudColors(batch, 'intensity', [0, 20]);
        expect(getPointCloudColors(batch, 'intensity', [0, 20])).toBe(first);
        const changedRange = getPointCloudColors(batch, 'intensity', [0, 40]);
        expect(changedRange).not.toEqual(first);
        const height = getPointCloudColors(batch, 'height');
        expect(height).not.toEqual(changedRange);
        const expected = new Float32Array(6);
        buildColorBuffer({ ...batch, colorMode: 'height', colors: expected });
        expect(height).toEqual(expected);
        const nextBatch = { ...batch, intensities: new Float32Array([20, 10]) };
        expect(getPointCloudColors(nextBatch, 'intensity', [0, 20])).not.toEqual(first);
        nextBatch.intensities = batch.intensities;
        expect(getPointCloudColors(nextBatch, 'intensity', [0, 20])).toEqual(first);
    });
});
