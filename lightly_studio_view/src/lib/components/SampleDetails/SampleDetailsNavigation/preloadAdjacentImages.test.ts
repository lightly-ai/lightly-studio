import { describe, expect, it, vi } from 'vitest';
import { preloadAdjacentImages } from './preloadAdjacentImages';

// Order of the samples: s1, s2 (current), s3, s4, s5, s6.
const NEXT: Record<string, string | null> = { s3: 's4', s4: 's5', s5: 's6', s6: null };

const defaultParams = {
    nextSampleId: 's3',
    previousSampleId: 's1',
    nextCount: 3,
    getNextSampleId: async (sampleId: string) => NEXT[sampleId],
    isCancelled: () => false
};

describe('preloadAdjacentImages', () => {
    it('preloads the next, the previous, then the samples after the next', async () => {
        const preloadImage = vi.fn();

        await preloadAdjacentImages({ ...defaultParams, preloadImage });

        expect(preloadImage.mock.calls.map(([sampleId]) => sampleId)).toEqual([
            's3',
            's1',
            's4',
            's5'
        ]);
    });

    it('stops at the end of the order', async () => {
        const preloadImage = vi.fn();

        await preloadAdjacentImages({
            ...defaultParams,
            nextSampleId: 's6',
            previousSampleId: null,
            preloadImage
        });

        expect(preloadImage.mock.calls.map(([sampleId]) => sampleId)).toEqual(['s6']);
    });

    it('stops when cancelled, for example after moving to another sample', async () => {
        const preloadImage = vi.fn();

        await preloadAdjacentImages({ ...defaultParams, isCancelled: () => true, preloadImage });

        expect(preloadImage.mock.calls.map(([sampleId]) => sampleId)).toEqual(['s3', 's1']);
    });

    it('keeps the preloaded images when a lookup fails', async () => {
        const preloadImage = vi.fn();

        await preloadAdjacentImages({
            ...defaultParams,
            getNextSampleId: async () => {
                throw new Error('network');
            },
            preloadImage
        });

        expect(preloadImage.mock.calls.map(([sampleId]) => sampleId)).toEqual(['s3', 's1']);
    });
});
