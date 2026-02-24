import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { SampleType } from '$lib/api/lightly_studio_local';
import type { ImageFilter } from '$lib/api/lightly_studio_local/types.gen';
import type { TextEmbedding } from '../useGlobalStorage';

const useAdjacentSamplesMock = vi.fn();
const imageFilterStore = writable<ImageFilter | null>(null);
const textEmbeddingStore = writable<TextEmbedding | undefined>(undefined);

vi.mock('../useAdjacentSamples/useAdjacentSamples', () => ({
    useAdjacentSamples: (...args: unknown[]) => useAdjacentSamplesMock(...args)
}));

vi.mock('../useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({
        imageFilter: imageFilterStore
    })
}));

vi.mock('../useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        textEmbedding: textEmbeddingStore
    })
}));

import { useAdjacentImages } from './useAdjacentImages';

describe('useAdjacentImages', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useAdjacentSamplesMock.mockReset();
        imageFilterStore.set({ sample_filter: { collection_id: 'collection-1' } });
        textEmbeddingStore.set({ embedding: [0.12, 0.34], queryText: 'cats' });
        useAdjacentSamplesMock.mockReturnValue({ query: 'query-result', refetch: vi.fn() });
    });

    it('delegates to useAdjacentSamples with image filters and text embedding', () => {
        const result = useAdjacentImages({ sampleId: 'sample-123', collectionId: 'collection-1' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'sample-123',
                body: {
                    sample_type: SampleType.IMAGE,
                    filters: { sample_filter: { collection_id: 'collection-1' } },
                    text_embedding: [0.12, 0.34]
                }
            }
        });
        expect(result).toEqual({ query: 'query-result', refetch: expect.any(Function) });
    });

    it('falls back to collectionId when filters are not ready', () => {
        imageFilterStore.set(null);

        useAdjacentImages({ sampleId: 'sample-789', collectionId: 'collection-1' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'sample-789',
                body: {
                    sample_type: SampleType.IMAGE,
                    filters: { sample_filter: { collection_id: 'collection-1' } },
                    text_embedding: [0.12, 0.34]
                }
            }
        });
    });

    it('sets text_embedding to undefined when no embedding is stored', () => {
        textEmbeddingStore.set(undefined);
        imageFilterStore.set({
            sample_filter: { collection_id: 'collection-2', tag_ids: ['tag-1'] }
        });

        useAdjacentImages({ sampleId: 'sample-456', collectionId: 'collection-2' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'sample-456',
                body: {
                    sample_type: SampleType.IMAGE,
                    filters: {
                        sample_filter: { collection_id: 'collection-2', tag_ids: ['tag-1'] }
                    },
                    text_embedding: undefined
                }
            }
        });
    });
});
