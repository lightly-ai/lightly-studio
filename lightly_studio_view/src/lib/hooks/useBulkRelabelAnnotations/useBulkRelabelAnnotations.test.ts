import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { readAnnotationLabelsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useBulkRelabelAnnotations } from './useBulkRelabelAnnotations';

const mocks = vi.hoisted(() => ({
    invalidateQueries: vi.fn(),
    invalidateAnnotationGridQueries: vi.fn(),
    invalidateEvaluationRunsQueries: vi.fn(),
    trackEvent: vi.fn(),
    bulkRelabelAnnotations: vi.fn(),
    bulkRelabelAnnotationsByFilter: vi.fn(),
    countsQueryKey: ['countImageAnnotations']
}));

vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries })
}));

vi.mock('$lib/api/lightly_studio_local', () => ({
    bulkRelabelAnnotations: mocks.bulkRelabelAnnotations,
    bulkRelabelAnnotationsByFilter: mocks.bulkRelabelAnnotationsByFilter
}));

vi.mock('$lib/hooks', () => ({
    useImageAnnotationCountsQueryKey: mocks.countsQueryKey,
    useInvalidateAnnotationGridQueries: () => mocks.invalidateAnnotationGridQueries,
    useInvalidateEvaluationRunsQueries: () => mocks.invalidateEvaluationRunsQueries,
    usePostHog: () => ({ trackEvent: mocks.trackEvent })
}));

const filter = { filter_type: 'annotations' as const };

const defaultInput = {
    collectionId: 'col-1',
    selectedIds: new Set(['a', 'b']),
    selectAllSnapshot: null,
    labelName: 'dog'
};

const idsResult = {
    previous_labels: [
        { annotation_id: 'a', label_name: 'cat' },
        { annotation_id: 'b', label_name: 'cat' }
    ]
};
const filterResult = {
    previous_labels: [
        { annotation_id: 'a', label_name: 'cat' },
        { annotation_id: 'b', label_name: 'cat' },
        { annotation_id: 'c', label_name: 'bird' }
    ]
};

const invalidatedKeys = () => mocks.invalidateQueries.mock.calls.map(([call]) => call.queryKey);

describe('useBulkRelabelAnnotations', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.bulkRelabelAnnotations.mockResolvedValue({
            data: idsResult,
            response: { status: 200 }
        });
        mocks.bulkRelabelAnnotationsByFilter.mockResolvedValue({
            data: filterResult,
            response: { status: 200 }
        });
    });

    it('relabels by ids when there is no select-all snapshot', async () => {
        const { relabelAnnotations } = useBulkRelabelAnnotations();

        const result = await relabelAnnotations(defaultInput);

        expect(mocks.bulkRelabelAnnotations).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: { annotation_ids: ['a', 'b'], label_name: 'dog' }
        });
        expect(mocks.bulkRelabelAnnotationsByFilter).not.toHaveBeenCalled();
        expect(result).toEqual({ data: idsResult });
    });

    it('relabels by ids when the selection differs from the select-all snapshot', async () => {
        const { relabelAnnotations } = useBulkRelabelAnnotations();

        await relabelAnnotations({ ...defaultInput, selectAllSnapshot: { filter, size: 3 } });

        expect(mocks.bulkRelabelAnnotations).toHaveBeenCalled();
        expect(mocks.bulkRelabelAnnotationsByFilter).not.toHaveBeenCalled();
    });

    it('relabels by filter for an unmodified select-all', async () => {
        const { relabelAnnotations } = useBulkRelabelAnnotations();

        const result = await relabelAnnotations({
            ...defaultInput,
            selectAllSnapshot: { filter, size: 2 }
        });

        expect(mocks.bulkRelabelAnnotationsByFilter).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: { filter, label_name: 'dog' }
        });
        expect(mocks.bulkRelabelAnnotations).not.toHaveBeenCalled();
        expect(result).toEqual({ data: filterResult });
    });

    it('invalidates the affected queries and tracks the relabel', async () => {
        const { relabelAnnotations } = useBulkRelabelAnnotations();

        await relabelAnnotations(defaultInput);

        expect(mocks.invalidateAnnotationGridQueries).toHaveBeenCalledWith('col-1');
        expect(mocks.invalidateEvaluationRunsQueries).toHaveBeenCalled();
        expect(invalidatedKeys()).toEqual(
            expect.arrayContaining([
                mocks.countsQueryKey,
                readAnnotationLabelsQueryKey({ path: { collection_id: 'col-1' } })
            ])
        );
        expect(mocks.trackEvent).toHaveBeenCalledWith('annotations_bulk_labeled', {
            collection_id: 'col-1',
            annotation_count: 2
        });
    });

    it('returns the error without refetching', async () => {
        mocks.bulkRelabelAnnotations.mockResolvedValue({
            error: { detail: 'Boom' },
            response: { status: 500 }
        });
        const { relabelAnnotations } = useBulkRelabelAnnotations();

        const result = await relabelAnnotations(defaultInput);

        expect(result).toEqual({ error: { detail: 'Boom' } });
        expect(mocks.invalidateQueries).not.toHaveBeenCalled();
    });

    it('returns a thrown error', async () => {
        const error = new Error('Network down');
        mocks.bulkRelabelAnnotations.mockRejectedValue(error);
        const { relabelAnnotations } = useBulkRelabelAnnotations();

        const result = await relabelAnnotations(defaultInput);

        expect(result).toEqual({ error });
    });

    it('is pending while the request runs', async () => {
        let resolveRequest: (value: unknown) => void = () => {};
        mocks.bulkRelabelAnnotations.mockReturnValue(
            new Promise((resolve) => {
                resolveRequest = resolve;
            })
        );
        const { relabelAnnotations, isPending } = useBulkRelabelAnnotations();

        const relabel = relabelAnnotations(defaultInput);
        expect(get(isPending)).toBe(true);

        resolveRequest({ data: idsResult, response: { status: 200 } });
        await relabel;
        expect(get(isPending)).toBe(false);
    });
});
