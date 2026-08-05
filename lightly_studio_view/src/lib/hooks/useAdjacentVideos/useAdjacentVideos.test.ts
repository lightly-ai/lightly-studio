import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { SampleType } from '$lib/api/lightly_studio_local';
import type { VideoFilter } from '$lib/api/lightly_studio_local/types.gen';
import type { TextEmbedding } from '../useGlobalStorage';
import type { VideoSortExpr } from '../useVideoFilters/useVideoFilters';

const useAdjacentSamplesMock = vi.fn();
const videoFilterStore = writable<VideoFilter | null>(null);
const videoSortByStore = writable<VideoSortExpr[] | null>(null);
const textEmbeddingStore = writable<TextEmbedding | undefined>(undefined);

vi.mock('../useAdjacentSamples/useAdjacentSamples', () => ({
    useAdjacentSamples: (...args: unknown[]) => useAdjacentSamplesMock(...args)
}));

vi.mock('../useVideoFilters/useVideoFilters', () => ({
    useVideoFilters: () => ({
        videoFilter: videoFilterStore,
        videoSortBy: videoSortByStore
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
        videoFilterStore.set({
            filter_type: 'video',
            sample_filter: { tag_ids: ['t1'] }
        });
        videoSortByStore.set([
            {
                source: 'metadata',
                field_name: 'min_caption_segment_match_score',
                direction: 'asc',
                is_numeric: true
            }
        ]);
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
                    collection_id: 'collection-1',
                    filters: {
                        filter_type: 'video',
                        sample_filter: { tag_ids: ['t1'] }
                    },
                    text_embedding: [0.11, 0.22],
                    sort_by: undefined
                }
            }
        });
        expect(result).toEqual({ query: 'query-result', refetch: expect.any(Function) });
    });

    it('passes videoSortBy when similarity search is inactive', () => {
        textEmbeddingStore.set(undefined);

        useAdjacentVideos({ sampleId: 'video-123', collectionId: 'collection-1' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'video-123',
                body: {
                    sample_type: SampleType.VIDEO,
                    collection_id: 'collection-1',
                    filters: {
                        filter_type: 'video',
                        sample_filter: { tag_ids: ['t1'] }
                    },
                    text_embedding: undefined,
                    sort_by: [
                        {
                            source: 'metadata',
                            field_name: 'min_caption_segment_match_score',
                            direction: 'asc',
                            is_numeric: true
                        }
                    ]
                }
            }
        });
    });

    it('calls useAdjacentSamplesMock with empty filters and undefined embedding when none are provided', () => {
        videoFilterStore.set(null);
        videoSortByStore.set(null);
        textEmbeddingStore.set(undefined);

        useAdjacentVideos({ sampleId: 'video-456', collectionId: 'collection-1' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'video-456',
                body: {
                    sample_type: SampleType.VIDEO,
                    collection_id: 'collection-1',
                    filters: {
                        filter_type: 'video'
                    },
                    text_embedding: undefined,
                    sort_by: undefined
                }
            }
        });
    });
});
