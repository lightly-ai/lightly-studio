import { describe, it, expect, vi, beforeEach } from 'vitest';
import { writable, type Writable } from 'svelte/store';
import { SampleType, type VideoFrameFilter } from '$lib/api/lightly_studio_local';
import { useAdjacentFrames } from './useAdjacentFrames';

const useAdjacentSamplesMock = vi.fn();
const frameFilterStore: Writable<VideoFrameFilter | null> = writable(null);

vi.mock('../useAdjacentSamples/useAdjacentSamples', () => ({
    useAdjacentSamples: (...args: unknown[]) => useAdjacentSamplesMock(...args)
}));

vi.mock('../useFramesFilter/useFramesFilter', () => ({
    useFramesFilter: () => ({
        frameFilter: frameFilterStore
    })
}));

describe('useAdjacentFrames', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        frameFilterStore.set(null);
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
                        sample_filter: { collection_id: 'col-1', sample_ids: ['a'] },
                        frame_number: { min: 1, max: 2 }
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
                        sample_filter: { collection_id: 'col-2' },
                        frame_number: {}
                    }
                }
            }
        });
    });
});
