import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type { SortField } from '$lib/hooks/useSortFields/useSortFields.svelte';
import { IMAGE_SORT_FIELDS } from '$lib/hooks/useSortFields/useSortFields.svelte';
import { useOrderBy } from './useOrderBy';
import type { SortExpr } from '../useImagesInfinite/types';

const imageSortBy = writable<SortExpr[] | null>(null);
const allSortFields = writable<SortField[]>([...IMAGE_SORT_FIELDS]);
const updateSortBy = vi.fn();

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({ imageSortBy, updateSortBy })
}));

vi.mock('$lib/hooks/useSortFields/useSortFields.svelte', async (importOriginal) => {
    const original =
        await importOriginal<typeof import('$lib/hooks/useSortFields/useSortFields.svelte')>();
    return {
        ...original,
        useSortFields: () => ({ allSortFields })
    };
});

describe('useOrderBy', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        imageSortBy.set(null);
        allSortFields.set([...IMAGE_SORT_FIELDS]);
    });

    describe('selectedDirection', () => {
        it('returns ASC when no sort is active', () => {
            const { selectedDirection } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });
            expect(get(selectedDirection)).toBe(SortDirection.ASC);
        });

        it('returns the direction of the active sort', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.DESC
                }
            ]);
            const { selectedDirection } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });
            expect(get(selectedDirection)).toBe(SortDirection.DESC);
        });
    });

    describe('selectedLabel', () => {
        it('returns null when no sort is active', () => {
            const { selectedLabel } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });
            expect(get(selectedLabel)).toBeNull();
        });

        it('returns the label for an active image sort field', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.ASC
                }
            ]);
            const { selectedLabel } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });
            expect(get(selectedLabel)).toBe('file name');
        });

        it('returns the metadata label when a metadata field is active', () => {
            allSortFields.set([
                ...IMAGE_SORT_FIELDS,
                {
                    source: 'metadata',
                    value: 'brightness',
                    label: 'metadata.brightness'
                }
            ]);
            imageSortBy.set([
                {
                    source: 'metadata',
                    field_name: 'brightness',
                    direction: SortDirection.ASC
                }
            ]);
            const { selectedLabel } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });
            expect(get(selectedLabel)).toBe('metadata.brightness');
        });

        it('returns a dot-formatted label when an evaluation metric is active', () => {
            allSortFields.set([
                ...IMAGE_SORT_FIELDS,
                {
                    source: 'evaluation_metric',
                    evaluation_run_name: 'run1',
                    metric_name: 'precision',
                    label: 'run1.precision'
                }
            ]);
            imageSortBy.set([
                {
                    source: 'evaluation_metric',
                    evaluation_run_name: 'run1',
                    metric_name: 'precision',
                    direction: SortDirection.ASC
                }
            ]);
            const { selectedLabel } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });
            expect(get(selectedLabel)).toBe('run1.precision');
        });
    });

    describe('isFieldSelected', () => {
        it('returns false for any field when no sort is active', () => {
            const { isFieldSelected } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });
            const check = get(isFieldSelected);

            expect(check({ source: 'image', value: 'file_name', label: 'file name' })).toBe(false);
        });

        it('returns true for the matching image field', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'width',
                    direction: SortDirection.ASC
                }
            ]);
            const { isFieldSelected } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });
            const check = get(isFieldSelected);

            expect(check({ source: 'image', value: 'width', label: 'width' })).toBe(true);
            expect(check({ source: 'image', value: 'height', label: 'height' })).toBe(false);
        });

        it('returns true for the matching evaluation metric field', () => {
            imageSortBy.set([
                {
                    source: 'evaluation_metric',
                    evaluation_run_name: 'run1',
                    metric_name: 'precision',
                    direction: SortDirection.ASC
                }
            ]);
            const { isFieldSelected } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });
            const check = get(isFieldSelected);

            expect(
                check({
                    source: 'evaluation_metric',
                    evaluation_run_name: 'run1',
                    metric_name: 'precision',
                    label: 'run1.precision'
                })
            ).toBe(true);
            expect(
                check({
                    source: 'evaluation_metric',
                    evaluation_run_name: 'run1',
                    metric_name: 'recall',
                    label: 'run1.recall'
                })
            ).toBe(false);
        });

        it('updates reactively when imageSortBy changes', () => {
            const { isFieldSelected } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });
            const field = { source: 'image' as const, value: 'width', label: 'width' };

            expect(get(isFieldSelected)(field)).toBe(false);

            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'width',
                    direction: SortDirection.ASC
                }
            ]);

            expect(get(isFieldSelected)(field)).toBe(true);
        });
    });

    describe('handleFieldClick', () => {
        it('selects an image field with ASC direction by default', () => {
            const { handleFieldClick } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });

            handleFieldClick({ source: 'image', value: 'file_name', label: 'file name' });

            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.ASC
                }
            ]);
        });

        it('deselects the field when clicking the already selected field', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.ASC
                }
            ]);
            const { handleFieldClick } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });

            handleFieldClick({ source: 'image', value: 'file_name', label: 'file name' });

            expect(updateSortBy).toHaveBeenCalledWith(null);
        });

        it('switches to a different field while preserving the current direction', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.DESC
                }
            ]);
            const { handleFieldClick } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });

            handleFieldClick({ source: 'image', value: 'width', label: 'width' });

            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'image',
                    field_name: 'width',
                    direction: SortDirection.DESC
                }
            ]);
        });

        it('selects a metadata field', () => {
            const { handleFieldClick } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });

            handleFieldClick({
                source: 'metadata',
                value: 'score',
                label: 'metadata.score'
            });

            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'metadata',
                    field_name: 'score',
                    direction: SortDirection.ASC
                }
            ]);
        });

        it('selects an evaluation metric field', () => {
            const { handleFieldClick } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });

            handleFieldClick({
                source: 'evaluation_metric',
                evaluation_run_name: 'run1',
                metric_name: 'precision',
                label: 'run1.precision'
            });

            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'evaluation_metric',
                    evaluation_run_name: 'run1',
                    metric_name: 'precision',
                    direction: SortDirection.ASC
                }
            ]);
        });
    });

    describe('toggleDirection', () => {
        it('does nothing when no sort is active', () => {
            const { toggleDirection } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });

            toggleDirection();

            expect(updateSortBy).not.toHaveBeenCalled();
        });

        it('toggles direction for an image field', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.ASC
                }
            ]);
            const { toggleDirection } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });

            toggleDirection();
            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.DESC
                }
            ]);

            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.DESC
                }
            ]);
            toggleDirection();
            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.ASC
                }
            ]);
        });

        it('toggles direction for a metadata field', () => {
            imageSortBy.set([
                {
                    source: 'metadata',
                    field_name: 'score',
                    direction: SortDirection.ASC
                }
            ]);
            const { toggleDirection } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });

            toggleDirection();

            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'metadata',
                    field_name: 'score',
                    direction: SortDirection.DESC
                }
            ]);
        });

        it('toggles direction for an evaluation metric field', () => {
            imageSortBy.set([
                {
                    source: 'evaluation_metric',
                    evaluation_run_name: 'run1',
                    metric_name: 'precision',
                    direction: SortDirection.ASC
                }
            ]);
            const { toggleDirection } = useOrderBy({
                collectionId: () => 'col1',
                datasetId: () => 'ds1'
            });

            toggleDirection();

            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'evaluation_metric',
                    evaluation_run_name: 'run1',
                    metric_name: 'precision',
                    direction: SortDirection.DESC
                }
            ]);
        });
    });
});
