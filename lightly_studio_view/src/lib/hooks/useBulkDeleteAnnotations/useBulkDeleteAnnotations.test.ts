import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import {
    readAnnotationCollectionsQueryKey,
    readAnnotationLabelsQueryKey,
    readCollectionHierarchyQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useBulkDeleteAnnotations } from './useBulkDeleteAnnotations';

const mocks = vi.hoisted(() => ({
    invalidateQueries: vi.fn(),
    invalidateAnnotationGridQueries: vi.fn(),
    invalidateEvaluationRunsQueries: vi.fn(),
    bulkDeleteAnnotations: vi.fn(),
    bulkDeleteAnnotationsByFilter: vi.fn(),
    countsQueryKey: ['countImageAnnotations']
}));

vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries })
}));

vi.mock('$lib/api/lightly_studio_local', () => ({
    bulkDeleteAnnotations: mocks.bulkDeleteAnnotations,
    bulkDeleteAnnotationsByFilter: mocks.bulkDeleteAnnotationsByFilter
}));

vi.mock('$lib/hooks', () => ({
    useImageAnnotationCountsQueryKey: mocks.countsQueryKey,
    useInvalidateAnnotationGridQueries: () => mocks.invalidateAnnotationGridQueries,
    useInvalidateEvaluationRunsQueries: () => mocks.invalidateEvaluationRunsQueries
}));

const filter = { filter_type: 'annotations' as const };

const defaultInput = {
    collectionId: 'col-1',
    rootCollectionId: 'root-1',
    selectedIds: new Set(['a', 'b']),
    selectAllSnapshot: null
};

const invalidatedKeys = () => mocks.invalidateQueries.mock.calls.map(([call]) => call.queryKey);

describe('useBulkDeleteAnnotations', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.bulkDeleteAnnotations.mockResolvedValue({
            data: { deleted_count: 2 },
            response: { status: 200 }
        });
        mocks.bulkDeleteAnnotationsByFilter.mockResolvedValue({
            data: { deleted_count: 5 },
            response: { status: 200 }
        });
    });

    it('deletes by ids when there is no select-all snapshot', async () => {
        const { deleteAnnotations } = useBulkDeleteAnnotations();

        const result = await deleteAnnotations(defaultInput);

        expect(mocks.bulkDeleteAnnotations).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: { annotation_ids: ['a', 'b'] }
        });
        expect(mocks.bulkDeleteAnnotationsByFilter).not.toHaveBeenCalled();
        expect(result).toEqual({ data: { deleted_count: 2 } });
    });

    it('deletes by ids when the selection differs from the select-all snapshot', async () => {
        const { deleteAnnotations } = useBulkDeleteAnnotations();

        await deleteAnnotations({ ...defaultInput, selectAllSnapshot: { filter, size: 3 } });

        expect(mocks.bulkDeleteAnnotations).toHaveBeenCalled();
        expect(mocks.bulkDeleteAnnotationsByFilter).not.toHaveBeenCalled();
    });

    it('deletes by filter for an unmodified select-all', async () => {
        const { deleteAnnotations } = useBulkDeleteAnnotations();

        const result = await deleteAnnotations({
            ...defaultInput,
            selectAllSnapshot: { filter, size: 2 }
        });

        expect(mocks.bulkDeleteAnnotationsByFilter).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: { filter }
        });
        expect(mocks.bulkDeleteAnnotations).not.toHaveBeenCalled();
        expect(result).toEqual({ data: { deleted_count: 5 } });
    });

    it('invalidates the affected queries after a delete', async () => {
        const { deleteAnnotations } = useBulkDeleteAnnotations();

        await deleteAnnotations(defaultInput);

        expect(mocks.invalidateAnnotationGridQueries).toHaveBeenCalledWith('col-1');
        expect(mocks.invalidateEvaluationRunsQueries).toHaveBeenCalled();
        expect(invalidatedKeys()).toEqual(
            expect.arrayContaining([
                mocks.countsQueryKey,
                readAnnotationCollectionsQueryKey({ path: { collection_id: 'col-1' } }),
                readAnnotationLabelsQueryKey({ path: { collection_id: 'col-1' } }),
                readCollectionHierarchyQueryKey({ path: { collection_id: 'root-1' } })
            ])
        );
    });

    it('returns the error without refetching', async () => {
        mocks.bulkDeleteAnnotations.mockResolvedValue({
            error: { detail: 'Boom' },
            response: { status: 500 }
        });
        const { deleteAnnotations } = useBulkDeleteAnnotations();

        const result = await deleteAnnotations(defaultInput);

        expect(result).toEqual({ error: { detail: 'Boom' } });
        expect(mocks.invalidateQueries).not.toHaveBeenCalled();
    });

    it('returns a thrown error', async () => {
        const error = new Error('Network down');
        mocks.bulkDeleteAnnotations.mockRejectedValue(error);
        const { deleteAnnotations } = useBulkDeleteAnnotations();

        const result = await deleteAnnotations(defaultInput);

        expect(result).toEqual({ error });
    });

    it('is pending while the request runs', async () => {
        let resolveRequest: (value: unknown) => void = () => {};
        mocks.bulkDeleteAnnotations.mockReturnValue(
            new Promise((resolve) => {
                resolveRequest = resolve;
            })
        );
        const { deleteAnnotations, isPending } = useBulkDeleteAnnotations();

        const deletion = deleteAnnotations(defaultInput);
        expect(get(isPending)).toBe(true);

        resolveRequest({ data: { deleted_count: 2 }, response: { status: 200 } });
        await deletion;
        expect(get(isPending)).toBe(false);
    });
});
