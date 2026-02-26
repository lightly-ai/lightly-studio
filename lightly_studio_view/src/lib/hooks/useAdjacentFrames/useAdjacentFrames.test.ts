import { describe, it, expect, vi, beforeEach } from 'vitest';
import { writable, type Writable } from 'svelte/store';
import {
    SampleType,
    type VideoFilter,
    type VideoFrameFilter
} from '$lib/api/lightly_studio_local';
import type { TextEmbedding } from '$lib/hooks/useGlobalStorage';
import { useAdjacentFrames } from './useAdjacentFrames';

const useAdjacentSamplesMock = vi.fn();
const frameFilterStore: Writable<VideoFrameFilter | null> = writable(null);
const videoFilterStore: Writable<VideoFilter | null> = writable(null);
const textEmbeddingStore = writable<TextEmbedding | undefined>(undefined);

vi.mock('../useAdjacentSamples/useAdjacentSamples', () => ({
    useAdjacentSamples: (...args: unknown[]) => useAdjacentSamplesMock(...args)
}));

vi.mock('../useFramesFilter/useFramesFilter', () => ({
    useFramesFilter: () => ({
        frameFilter: frameFilterStore
    })
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

describe('useAdjacentFrames', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        frameFilterStore.set(null);
        videoFilterStore.set(null);
        textEmbeddingStore.set(undefined);
        useAdjacentSamplesMock.mockReturnValue({ query: 'result' });
    });

    it('passes the derived frameFilter to useAdjacentSamples', () => {
        frameFilterStore.set({
            sample_filter: { collection_id: 'col-1', sample_ids: ['a'] },
            frame_number: { min: 1, max: 2 }
        });

        const result = useAdjacentFrames({ sampleId: 'frame-1', collectionId: 'col-1' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'frame-1',
                body: {
                    sample_type: SampleType.VIDEO_FRAME,
                    filters: {
                        video_frame_filter: {
                            sample_filter: { collection_id: 'col-1', sample_ids: ['a'] },
                            frame_number: { min: 1, max: 2 }
                        }
                    }
                }
            }
        });
        expect(result).toEqual({ query: 'result' });
    });

    it('falls back to default filters when frameFilter is null', () => {
        frameFilterStore.set(null);

        useAdjacentFrames({ sampleId: 'frame-2', collectionId: 'col-2' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'frame-2',
                body: {
                    sample_type: SampleType.VIDEO_FRAME,
                    filters: {
                        video_frame_filter: {
                            sample_filter: { collection_id: 'col-2' },
                            frame_number: {}
                        }
                    }
                }
            }
        });
    });

    it('includes video filter and text embedding when fetching from videos', () => {
        videoFilterStore.set({
            sample_filter: {
                collection_id: 'col-3',
                sample_ids: ['s1']
            }
        });
        textEmbeddingStore.set({ embedding: [0.1, 0.2], queryText: 'car' });

        useAdjacentFrames({ sampleId: 'frame-3', collectionId: 'col-3', fromVideos: true });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'frame-3',
                body: {
                    sample_type: SampleType.VIDEO_FRAME,
                    filters: {
                        video_frame_filter: {
                            sample_filter: { collection_id: 'col-3' },
                            frame_number: {}
                        },
                        video_filter: {
                            sample_filter: {
                                collection_id: 'col-3',
                                sample_ids: ['s1']
                            }
                        },
                        video_text_embedding: [0.1, 0.2]
                    }
                }
            }
        });
    });
});
