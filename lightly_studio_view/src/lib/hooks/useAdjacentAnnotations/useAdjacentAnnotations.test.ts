import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { SampleType, type AnnotationEvaluationMetricSortExpr } from '$lib/api/lightly_studio_local';
import type { TextEmbedding } from '$lib/hooks/useGlobalStorage';

const useAdjacentSamplesMock = vi.fn();
const selectedAnnotationFilterIds = writable<Set<string>>(new Set());
const tagsSelected = writable<Set<string>>(new Set());
const textEmbedding = writable<TextEmbedding | undefined>(undefined);
const getSortByMock = vi.fn<(collectionId: string) => AnnotationEvaluationMetricSortExpr | null>();
const hasEmbeddingsQueryStore = writable<{ data: boolean | undefined }>({ data: undefined });

vi.mock('../useAdjacentSamples/useAdjacentSamples', () => ({
    useAdjacentSamples: (...args: unknown[]) => useAdjacentSamplesMock(...args)
}));

vi.mock('../useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        selectedAnnotationFilterIds,
        textEmbedding
    })
}));

vi.mock('../useTags/useTags', () => ({
    useTags: () => ({
        tagsSelected
    })
}));

vi.mock('$lib/hooks', () => ({
    useAnnotationSortBy: () => ({ getSortBy: getSortByMock })
}));

vi.mock('../useHasEmbeddings/useHasEmbeddings', () => ({
    useHasEmbeddings: () => hasEmbeddingsQueryStore
}));

import { useAdjacentAnnotations } from './useAdjacentAnnotations';

describe('useAdjacentAnnotations', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useAdjacentSamplesMock.mockReset();
        selectedAnnotationFilterIds.set(new Set());
        tagsSelected.set(new Set());
        textEmbedding.set(undefined);
        hasEmbeddingsQueryStore.set({ data: undefined });
        getSortByMock.mockReturnValue(null);
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
                    collection_id: 'col-9',
                    filters: {
                        filter_type: 'annotations',
                        collection_ids: ['col-9'],
                        annotation_label_ids: ['label-1', 'label-2'],
                        tag_ids: ['tag-1']
                    },
                    annotation_sort_by: undefined
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
                    collection_id: 'col-3',
                    filters: {
                        filter_type: 'annotations',
                        collection_ids: ['col-3'],
                        annotation_label_ids: undefined,
                        tag_ids: undefined
                    },
                    annotation_sort_by: undefined
                }
            }
        });
    });

    it('passes annotation_sort_by to useAdjacentSamples when a sort is active', () => {
        const sort: AnnotationEvaluationMetricSortExpr = {
            evaluation_run_id: 'run-1',
            metric_name: 'iou',
            direction: 'desc'
        };
        getSortByMock.mockReturnValue(sort);

        useAdjacentAnnotations({ sampleId: 'ann-123', collectionId: 'col-9' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({
                    body: expect.objectContaining({ annotation_sort_by: sort })
                })
            })
        );
    });

    it('suppresses annotation_sort_by when a similarity search is active on a collection with embeddings', () => {
        const sort: AnnotationEvaluationMetricSortExpr = {
            evaluation_run_id: 'run-1',
            metric_name: 'iou',
            direction: 'desc'
        };
        getSortByMock.mockReturnValue(sort);
        hasEmbeddingsQueryStore.set({ data: true });
        textEmbedding.set({ queryText: 'a dog', embedding: [0.1, 0.2] });

        useAdjacentAnnotations({ sampleId: 'ann-123', collectionId: 'col-9' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({
                    body: expect.objectContaining({ annotation_sort_by: undefined })
                })
            })
        );
    });

    it('keeps annotation_sort_by when a search embedding is set but the collection has no embeddings', () => {
        const sort: AnnotationEvaluationMetricSortExpr = {
            evaluation_run_id: 'run-1',
            metric_name: 'iou',
            direction: 'desc'
        };
        getSortByMock.mockReturnValue(sort);
        hasEmbeddingsQueryStore.set({ data: false });
        textEmbedding.set({ queryText: 'a dog', embedding: [0.1, 0.2] });

        useAdjacentAnnotations({ sampleId: 'ann-123', collectionId: 'col-9' });

        expect(useAdjacentSamplesMock).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({
                    body: expect.objectContaining({ annotation_sort_by: sort })
                })
            })
        );
    });
});
