import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readable } from 'svelte/store';
import { useQueryClient } from '@tanstack/svelte-query';
import {
    createClassificationAnnotations,
    createClassificationAnnotationsByFilter
} from '$lib/api/lightly_studio_local/sdk.gen';
import { useBulkAddAnnotationClass } from './useBulkAddAnnotationClass';

vi.mock('@tanstack/svelte-query', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/svelte-query')>();
    return { ...actual, useQueryClient: vi.fn() };
});

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    createClassificationAnnotations: vi.fn(),
    createClassificationAnnotationsByFilter: vi.fn()
}));

const trackEvent = vi.fn();
vi.mock('$lib/hooks/usePostHog', () => ({ usePostHog: () => ({ trackEvent }) }));

const { getSelectAllSnapshot } = vi.hoisted(() => ({ getSelectAllSnapshot: vi.fn() }));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ getSelectAllSnapshot })
}));

const { invalidateAnnotationGridQueries, useInvalidateAnnotationGridQueries } = vi.hoisted(() => ({
    invalidateAnnotationGridQueries: vi.fn(),
    useInvalidateAnnotationGridQueries: vi.fn()
}));
vi.mock('$lib/hooks/useInvalidateAnnotationGridQueries', () => ({
    useInvalidateAnnotationGridQueries
}));

const snapshotFilter = { filter_type: 'image' as const, sample_filter: { tag_ids: ['tag-1'] } };
const created = { created_annotation_ids: ['ann-1'], created_count: 1, skipped_count: 2 };

describe('useBulkAddAnnotationClass', () => {
    const invalidateQueries = vi.fn();

    const setSnapshot = (snapshot: { filter: typeof snapshotFilter; size: number } | null) => {
        getSelectAllSnapshot.mockReturnValue(readable(snapshot));
    };

    const addAnnotationClass = (selectedSampleIds: Set<string>) =>
        useBulkAddAnnotationClass({ getCollectionId: () => 'col-1' }).addAnnotationClass({
            className: 'dog',
            annotationSource: 'ground-truth',
            selectedSampleIds
        });

    beforeEach(() => {
        vi.clearAllMocks();
        useInvalidateAnnotationGridQueries.mockReturnValue(invalidateAnnotationGridQueries);
        vi.mocked(useQueryClient).mockReturnValue({ invalidateQueries } as unknown as ReturnType<
            typeof useQueryClient
        >);
        vi.mocked(createClassificationAnnotations).mockResolvedValue({
            data: created
        } as unknown as Awaited<ReturnType<typeof createClassificationAnnotations>>);
        vi.mocked(createClassificationAnnotationsByFilter).mockResolvedValue({
            data: created
        } as unknown as Awaited<ReturnType<typeof createClassificationAnnotationsByFilter>>);
        setSnapshot(null);
    });

    it('sends the snapshot filter while the selection is still an unmodified select-all', async () => {
        setSnapshot({ filter: snapshotFilter, size: 2 });

        await addAnnotationClass(new Set(['s-1', 's-2']));

        expect(createClassificationAnnotationsByFilter).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: {
                class_name: 'dog',
                annotation_collection_name: 'ground-truth',
                filter: snapshotFilter
            },
            throwOnError: true
        });
        expect(createClassificationAnnotations).not.toHaveBeenCalled();
    });

    it('sends the sample IDs when there is no select-all snapshot', async () => {
        await addAnnotationClass(new Set(['s-1', 's-2']));

        expect(createClassificationAnnotations).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: {
                class_name: 'dog',
                annotation_collection_name: 'ground-truth',
                sample_ids: ['s-1', 's-2']
            },
            throwOnError: true
        });
        expect(createClassificationAnnotationsByFilter).not.toHaveBeenCalled();
    });

    it('falls back to the sample IDs when a select-all had one image deselected', async () => {
        setSnapshot({ filter: snapshotFilter, size: 3 });

        await addAnnotationClass(new Set(['s-1', 's-2']));

        expect(createClassificationAnnotations).toHaveBeenCalledWith(
            expect.objectContaining({
                body: expect.objectContaining({ sample_ids: ['s-1', 's-2'] })
            })
        );
        expect(createClassificationAnnotationsByFilter).not.toHaveBeenCalled();
    });

    it('invalidates the annotation grids, counts, pickers and evaluation runs on success', async () => {
        await addAnnotationClass(new Set(['s-1']));

        expect(invalidateAnnotationGridQueries).toHaveBeenCalledWith('col-1');
        expect(
            invalidateQueries.mock.calls.map(([{ queryKey }]) => ({
                id: queryKey[0]._id,
                collectionId: queryKey[0].path?.collection_id
            }))
        ).toEqual([
            { id: 'countImageAnnotationsByCollection', collectionId: '__static_value__' },
            { id: 'readAnnotationCollections', collectionId: 'col-1' },
            { id: 'readAnnotationLabels', collectionId: 'col-1' },
            { id: 'getEvaluationRuns', collectionId: undefined }
        ]);
    });

    it('reports the created and skipped counts and tracks the event', async () => {
        const result = await addAnnotationClass(new Set(['s-1']));

        expect(result).toEqual(created);
        expect(trackEvent).toHaveBeenCalledWith('annotations_bulk_labeled', {
            collection_id: 'col-1',
            selected_count: 1,
            created_count: 1,
            skipped_count: 2
        });
    });

    it('does not invalidate when the request fails', async () => {
        vi.mocked(createClassificationAnnotations).mockRejectedValue(new Error('boom'));

        await expect(addAnnotationClass(new Set(['s-1']))).rejects.toThrow('boom');
        expect(invalidateAnnotationGridQueries).not.toHaveBeenCalled();
        expect(invalidateQueries).not.toHaveBeenCalled();
    });
});
