import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { SampleType } from '$lib/api/lightly_studio_local';
import type { VideoFrameFieldsBoundsView } from '$lib/api/lightly_studio_local/types.gen';

type MetadataValues = Record<string, { min: number; max: number }>;

const useAdjacentSamplesMock = vi.fn();
const selectedAnnotationFilterIdsStore = writable<Set<string>>(new Set());
const tagsSelectedStore = writable<Set<string>>(new Set());
const videoFramesBoundsValuesStore = writable<VideoFrameFieldsBoundsView | null>(null);
const metadataValuesStore = writable<MetadataValues | null>(null);
const createMetadataFiltersMock = vi.fn();

vi.mock('../useAdjacentSamples/useAdjacentSamples', () => ({
    useAdjacentSamples: (...args: unknown[]) => useAdjacentSamplesMock(...args)
}));

vi.mock('../useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        selectedAnnotationFilterIds: selectedAnnotationFilterIdsStore
    })
}));

vi.mock('../useTags/useTags', () => ({
    useTags: () => ({
        tagsSelected: tagsSelectedStore
    })
}));

vi.mock('../useVideoFramesBounds/useVideoFramesBounds', () => ({
    useVideoFramesBounds: () => ({
        videoFramesBoundsValues: videoFramesBoundsValuesStore
    })
}));

vi.mock('../useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: () => ({
        metadataValues: metadataValuesStore
    }),
    createMetadataFilters: (...args: unknown[]) => createMetadataFiltersMock(...args)
}));

import { useAdjacentFrames } from './useAdjacentFrames';

describe('useAdjacentFrames', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useAdjacentSamplesMock.mockReset();
        createMetadataFiltersMock.mockReset();

        selectedAnnotationFilterIdsStore.set(new Set(['ann-1', 'ann-2']));
        tagsSelectedStore.set(new Set(['tag-1']));
        videoFramesBoundsValuesStore.set({
            frame_number: { min: 10, max: 20 }
        });
        metadataValuesStore.set({ brightness: { min: 0, max: 100 } });

        createMetadataFiltersMock.mockReturnValue([
            { key: 'brightness', value: 0, op: '>=' },
            { key: 'brightness', value: 100, op: '<=' }
        ]);

        useAdjacentSamplesMock.mockReturnValue({ query: 'query-result', refetch: vi.fn() });
    });

    it('calls createMetadataFilters and useAdjacentSamplesMock with store-derived filters and returns its result', () => {
        const result = useAdjacentFrames({
            sampleId: 'frame-123',
            collectionId: 'collection-123'
        });

        expect(createMetadataFiltersMock).toHaveBeenCalledWith({
            brightness: { min: 0, max: 100 }
        });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'frame-123',
                body: {
                    sample_type: SampleType.VIDEO_FRAME,
                    filters: {
                        sample_filter: {
                            collection_id: 'collection-123',
                            annotation_label_ids: ['ann-1', 'ann-2'],
                            tag_ids: ['tag-1'],
                            metadata_filters: [
                                { key: 'brightness', value: 0, op: '>=' },
                                { key: 'brightness', value: 100, op: '<=' }
                            ]
                        },
                        frame_number: { min: 10, max: 20 }
                    }
                }
            }
        });
        expect(result).toEqual({ query: 'query-result', refetch: expect.any(Function) });
    });

    it('calls useAdjacentSamplesMock without label, tag, or metadata filters when stores are empty', () => {
        selectedAnnotationFilterIdsStore.set(new Set());
        tagsSelectedStore.set(new Set());
        metadataValuesStore.set({});
        videoFramesBoundsValuesStore.set({
            frame_number: { min: 1, max: 1 }
        });
        createMetadataFiltersMock.mockReturnValue([]);

        useAdjacentFrames({
            sampleId: 'frame-456',
            collectionId: 'collection-xyz'
        });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'frame-456',
                body: {
                    sample_type: SampleType.VIDEO_FRAME,
                    filters: {
                        sample_filter: {
                            collection_id: 'collection-xyz',
                            annotation_label_ids: undefined,
                            tag_ids: undefined,
                            metadata_filters: []
                        },
                        frame_number: { min: 1, max: 1 }
                    }
                }
            }
        });
    });
});
