import { describe, expect, it } from 'vitest';
import type { CloudPointFrame } from '$lib/hooks/useCloudPointFrame/types';
import { accumulatePointCloud } from './pointCloudAccumulation';

const createFrame = (timestampNs: string, positions: number[]): CloudPointFrame => ({
    batch: {
        positions: new Float32Array(positions),
        intensities: new Float32Array(positions.length / 3),
        count: positions.length / 3
    },
    channelId: 1,
    timestampNs,
    frameId: 'map',
    sourcePointCount: positions.length / 3,
    bounds: null,
    channels: [{ channelId: 1, timestampNs, frameId: 'map' }]
});

describe('accumulatePointCloud', () => {
    it('merges the points of new frames into the collected ones', () => {
        const first = accumulatePointCloud(null, 'key', createFrame('1', [1, 2, 3]));
        const second = accumulatePointCloud(first, 'key', createFrame('2', [4, 5, 6]));

        expect(second.batch.count).toBe(2);
        expect(Array.from(second.batch.positions)).toEqual([1, 2, 3, 4, 5, 6]);
    });

    it('does not add a frame twice', () => {
        const first = accumulatePointCloud(null, 'key', createFrame('1', [1, 2, 3]));

        expect(accumulatePointCloud(first, 'key', createFrame('1', [1, 2, 3]))).toBe(first);
    });

    it('starts over when the key changes', () => {
        const first = accumulatePointCloud(null, 'map', createFrame('1', [1, 2, 3]));
        const restarted = accumulatePointCloud(first, 'CABIN', createFrame('2', [4, 5, 6]));

        expect(restarted.batch.count).toBe(1);
        expect(Array.from(restarted.batch.positions)).toEqual([4, 5, 6]);
    });
});
