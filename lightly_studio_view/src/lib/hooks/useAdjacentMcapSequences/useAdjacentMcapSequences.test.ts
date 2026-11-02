import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { SampleType } from '$lib/api/lightly_studio_local';
import type { McapSequenceFilter } from '$lib/api/lightly_studio_local/types.gen';
import type { TextEmbedding } from '../useGlobalStorage';

const useAdjacentSamplesMock = vi.fn();
const mcapSequenceFilterStore = writable<McapSequenceFilter | null>(null);
const textEmbeddingStore = writable<TextEmbedding | undefined>(undefined);

vi.mock('../useAdjacentSamples/useAdjacentSamples', () => ({
    useAdjacentSamples: (...args: unknown[]) => useAdjacentSamplesMock(...args)
}));

vi.mock('../useMcapSequenceFilters/useMcapSequenceFilters', () => ({
    useMcapSequenceFilters: () => ({
        mcapSequenceFilter: mcapSequenceFilterStore
    })
}));

vi.mock('../useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        textEmbedding: textEmbeddingStore
    })
}));

import { useAdjacentMcapSequences } from './useAdjacentMcapSequences';

describe('useAdjacentMcapSequences', () => {
    beforeEach(() => {
        useAdjacentSamplesMock.mockReset();
        useAdjacentSamplesMock.mockReturnValue({ query: 'query-result', refetch: vi.fn() });
        mcapSequenceFilterStore.set(null);
        textEmbeddingStore.set(undefined);
    });

    it('sends the grid filter and text embedding', () => {
        const filter: McapSequenceFilter = {
            filter_type: 'mcap_sequence',
            sample_filter: { tag_ids: ['tag-1'] }
        };
        mcapSequenceFilterStore.set(filter);
        textEmbeddingStore.set({ embedding: [0.12, 0.34], queryText: 'cars' });

        const result = useAdjacentMcapSequences({
            sampleId: 'sequence-1',
            collectionId: 'collection-1'
        });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'sequence-1',
                body: {
                    sample_type: SampleType.SEQUENCE,
                    collection_id: 'collection-1',
                    filters: filter,
                    text_embedding: [0.12, 0.34]
                }
            }
        });
        expect(result).toEqual({ query: 'query-result', refetch: expect.any(Function) });
    });

    it('sends no filter and no text embedding when the grid has none', () => {
        useAdjacentMcapSequences({ sampleId: 'sequence-1', collectionId: 'collection-1' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'sequence-1',
                body: {
                    sample_type: SampleType.SEQUENCE,
                    collection_id: 'collection-1',
                    filters: undefined,
                    text_embedding: undefined
                }
            }
        });
    });
});
