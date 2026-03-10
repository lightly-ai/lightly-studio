import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { SampleType } from '$lib/api/lightly_studio_local';
import type { VideoFilter } from '$lib/api/lightly_studio_local/types.gen';
import type { TextEmbedding } from '../useGlobalStorage';

const useAdjacentSamplesMock = vi.fn();
const videoFilterStore = writable<VideoFilter | null>(null);
const textEmbeddingStore = writable<TextEmbedding | undefined>(undefined);

vi.mock('../useAdjacentSamples/useAdjacentSamples', () => ({
    useAdjacentSamples: (...args: unknown[]) => useAdjacentSamplesMock(...args)
}));

vi.mock('../useVideoFilters/useVideoFilters', () => ({
    useVideoFilters: () => ({
        videoFilter: videoFilterStore
    })
}));

vi.mock('../useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        textEmbedding: textEmbeddingStore
    })
}));

import { useAdjacentVideos } from './useAdjacentVideos';

describe('useAdjacentVideos', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useAdjacentSamplesMock.mockReset();
        videoFilterStore.set({ sample_filter: { collection_id: 'collection-1', tag_ids: ['t1'] } });
        textEmbeddingStore.set({ embedding: [0.11, 0.22], queryText: 'query' });
        useAdjacentSamplesMock.mockReturnValue({ query: 'query-result', refetch: vi.fn() });
    });

    it('calls useAdjacentSamplesMock with video filters and text embedding and returns its result', () => {
        const result = useAdjacentVideos({ sampleId: 'video-123', collectionId: 'collection-1' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'video-123',
                body: {
                    sample_type: SampleType.VIDEO,
                    filters: { sample_filter: { collection_id: 'collection-1', tag_ids: ['t1'] } },
                    text_embedding: [0.11, 0.22]
                }
            }
        });
        expect(result).toEqual({ query: 'query-result', refetch: expect.any(Function) });
    });

    it('calls useAdjacentSamplesMock with empty filters and undefined embedding when none are provided', () => {
        videoFilterStore.set(null);
        textEmbeddingStore.set(undefined);

        useAdjacentVideos({ sampleId: 'video-456', collectionId: 'collection-1' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'video-456',
                body: {
                    sample_type: SampleType.VIDEO,
                    filters: {
                        sample_filter: {
                            collection_id: 'collection-1'
                        }
                    },
                    text_embedding: undefined
                }
            }
        });
    });
});
