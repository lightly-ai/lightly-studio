import { describe, expect, it, vi } from 'vitest';
import { SampleType } from '$lib/api/lightly_studio_local';

const useAdjacentSamplesMock = vi.fn();

vi.mock('../useAdjacentSamples/useAdjacentSamples', () => ({
    useAdjacentSamples: (...args: unknown[]) => useAdjacentSamplesMock(...args)
}));

import { useAdjacentMcapSequences } from './useAdjacentMcapSequences';

describe('useAdjacentMcapSequences', () => {
    it('requests sequence adjacents for the collection and returns the result', () => {
        useAdjacentSamplesMock.mockReturnValue({ query: 'query-result', refetch: vi.fn() });

        const result = useAdjacentMcapSequences({
            sampleId: 'sequence-1',
            collectionId: 'collection-1'
        });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'sequence-1',
                body: {
                    sample_type: SampleType.SEQUENCE,
                    collection_id: 'collection-1'
                }
            }
        });
        expect(result).toEqual({ query: 'query-result', refetch: expect.any(Function) });
    });
});
