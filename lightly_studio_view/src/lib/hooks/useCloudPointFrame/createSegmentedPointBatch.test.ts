import { describe, expect, it, vi } from 'vitest';
import * as merging from './mergePointBatches';
import { createSegmentedPointBatch } from './createSegmentedPointBatch';

describe('segmented point batches', () => {
    it('retains the original sensor buffers and packs compatibility arrays only once on demand', () => {
        const merge = vi.spyOn(merging, 'mergePointBatches');
        const segments = [
            {
                positions: new Float32Array([1, 2, 3]),
                intensities: new Float32Array([10]),
                count: 1
            },
            {
                positions: new Float32Array([4, 5, 6]),
                intensities: new Float32Array([20]),
                count: 1
            }
        ];
        try {
            const batch = createSegmentedPointBatch(segments);
            expect(batch.segments).toBe(segments);
            expect(batch.count).toBe(2);
            expect(merge).not.toHaveBeenCalled();
            expect(Array.from(batch.positions)).toEqual([1, 2, 3, 4, 5, 6]);
            expect(Array.from(batch.intensities)).toEqual([10, 20]);
            expect(batch.positions).toBe(batch.positions);
            expect(merge).toHaveBeenCalledOnce();
        } finally {
            merge.mockRestore();
        }
    });
});
