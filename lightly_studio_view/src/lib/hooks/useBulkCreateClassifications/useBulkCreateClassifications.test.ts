import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readAnnotationCollectionsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import {
    formatBulkCreateToast,
    shouldBulkCreateByFilter,
    useBulkCreateClassifications
} from './useBulkCreateClassifications.svelte';

const mocks = vi.hoisted(() => ({
    invalidateQueries: vi.fn(),
    bulkCreateClassifications: vi.fn(),
    countsQueryKey: ['countImageAnnotations']
}));

vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries })
}));

vi.mock('$lib/api/lightly_studio_local', () => ({
    bulkCreateClassifications: mocks.bulkCreateClassifications,
    bulkCreateClassificationsByFilter: vi.fn()
}));

vi.mock('$lib/hooks', () => ({
    useImageAnnotationCountsQueryKey: mocks.countsQueryKey,
    useInvalidateAnnotationGridQueries: () => vi.fn(),
    useInvalidateEvaluationRunsQueries: () => vi.fn(),
    usePostHog: () => ({ trackEvent: vi.fn() })
}));

vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const filter = { filter_type: 'image' as const };

describe('shouldBulkCreateByFilter', () => {
    it('uses the filter route only for an intact select-all snapshot', () => {
        expect(
            shouldBulkCreateByFilter({
                selectAllSnapshot: { filter, size: 2 },
                selectedIds: new Set(['a', 'b'])
            })
        ).toBe(true);

        expect(
            shouldBulkCreateByFilter({
                selectAllSnapshot: { filter, size: 3 },
                selectedIds: new Set(['a', 'b'])
            })
        ).toBe(false);

        expect(
            shouldBulkCreateByFilter({
                selectAllSnapshot: null,
                selectedIds: new Set(['a', 'b'])
            })
        ).toBe(false);
    });
});

describe('formatBulkCreateToast', () => {
    it('formats created and skipped outcomes', () => {
        expect(
            formatBulkCreateToast(
                { created_annotation_ids: ['a'], created_count: 40, skipped_count: 0 },
                40
            )
        ).toBe('Added the annotation class to 40 images.');
        expect(
            formatBulkCreateToast(
                { created_annotation_ids: ['a'], created_count: 28, skipped_count: 12 },
                40
            )
        ).toBe('Added to 28 of 40 images; 12 already had this annotation class.');
        expect(
            formatBulkCreateToast(
                { created_annotation_ids: [], created_count: 0, skipped_count: 5 },
                5
            )
        ).toBe('No images changed; all 5 already had this annotation class.');
    });
});

describe('useBulkCreateClassifications', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.invalidateQueries.mockResolvedValue(undefined);
        mocks.bulkCreateClassifications.mockResolvedValue({
            data: { created_annotation_ids: ['a'], created_count: 1, skipped_count: 0 }
        });
    });

    it('refetches the annotation sources before the sidebar counts', async () => {
        const { addClass } = useBulkCreateClassifications();

        await addClass({
            collectionId: 'col-1',
            selectedIds: new Set(['s1']),
            className: 'dog',
            sourceName: 'annotation',
            selectAllSnapshot: null,
            rootCollectionId: 'root-1'
        });
        await vi.waitFor(() =>
            expect(mocks.invalidateQueries).toHaveBeenCalledWith({
                queryKey: mocks.countsQueryKey
            })
        );

        const invalidatedKeys = mocks.invalidateQueries.mock.calls.map(([call]) => call.queryKey);
        const sourcesIndex = invalidatedKeys.findIndex(
            (key) =>
                JSON.stringify(key) ===
                JSON.stringify(
                    readAnnotationCollectionsQueryKey({ path: { collection_id: 'col-1' } })
                )
        );
        const countsIndex = invalidatedKeys.findIndex(
            (key) => JSON.stringify(key) === JSON.stringify(mocks.countsQueryKey)
        );

        expect(sourcesIndex).toBeGreaterThanOrEqual(0);
        expect(countsIndex).toBeGreaterThan(sourcesIndex);
    });
});
