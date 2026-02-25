import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { SampleType } from '$lib/api/lightly_studio_local';

const useAdjacentSamplesMock = vi.fn();
const selectedAnnotationFilterIds = writable<Set<string>>(new Set());
const tagsSelected = writable<Set<string>>(new Set());

vi.mock('../useAdjacentSamples/useAdjacentSamples', () => ({
    useAdjacentSamples: (...args: unknown[]) => useAdjacentSamplesMock(...args)
}));

vi.mock('../useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        selectedAnnotationFilterIds
    })
}));

vi.mock('../useTags/useTags', () => ({
    useTags: () => ({
        tagsSelected
    })
}));

import { useAdjacentAnnotations } from './useAdjacentAnnotations';

describe('useAdjacentAnnotations', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useAdjacentSamplesMock.mockReset();
        selectedAnnotationFilterIds.set(new Set());
        tagsSelected.set(new Set());
        useAdjacentSamplesMock.mockReturnValue({ query: 'query-result', refetch: vi.fn() });
    });

    it('calls useAdjacentSamplesMock with selected labels and tags and returns its result', () => {
        selectedAnnotationFilterIds.set(new Set(['label-1', 'label-2']));
        tagsSelected.set(new Set(['tag-1']));

        const result = useAdjacentAnnotations({ sampleId: 'ann-123', collectionId: 'col-9' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'ann-123',
                body: {
                    sample_type: SampleType.ANNOTATION,
                    filters: {
                        collection_ids: ['col-9'],
                        annotation_label_ids: ['label-1', 'label-2'],
                        annotation_tag_ids: ['tag-1']
                    }
                }
            }
        });
        expect(result).toEqual({ query: 'query-result', refetch: expect.any(Function) });
    });

    it('calls useAdjacentSamplesMock without label or tag filters when none are selected', () => {
        useAdjacentAnnotations({ sampleId: 'ann-456', collectionId: 'col-3' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith({
            params: {
                sampleId: 'ann-456',
                body: {
                    sample_type: SampleType.ANNOTATION,
                    filters: {
                        collection_ids: ['col-3'],
                        annotation_label_ids: undefined,
                        annotation_tag_ids: undefined
                    }
                }
            }
        });
    });
});
