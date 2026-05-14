import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type { MetadataInfoView } from '$lib/api/lightly_studio_local';
import type { EvaluationRunMetricsInfoView } from '$lib/api/lightly_studio_local/types.gen';
import type { SortExpr } from '$lib/hooks/useImagesInfinite/useImagesInfinite';
import { useOrderBy } from './useOrderBy';

const imageSortBy = writable<SortExpr[] | null>(null);
const metadataInfo = writable<MetadataInfoView[]>([]);
const metricsInfo = writable<{ data: EvaluationRunMetricsInfoView[] | null }>({ data: null });
const updateSortBy = vi.fn();

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({ imageSortBy, updateSortBy })
}));

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: () => ({ metadataInfo })
}));

vi.mock('$lib/hooks/useEvaluationSampleMetricsInfo/useEvaluationSampleMetricsInfo', () => ({
    useEvaluationSampleMetricsInfo: () => metricsInfo
}));

describe('useOrderBy', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        imageSortBy.set(null);
        metadataInfo.set([]);
        metricsInfo.set({ data: null });
    });

    describe('allSortFields', () => {
        it('contains the five base image sort fields', () => {
            const { allSortFields } = useOrderBy({ datasetId: 'ds1' });
            const fields = get(allSortFields);

            expect(fields).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({ source: 'image', value: 'file_name' }),
                    expect.objectContaining({ source: 'image', value: 'file_path_abs' }),
                    expect.objectContaining({ source: 'image', value: 'created_at' }),
                    expect.objectContaining({ source: 'image', value: 'width' }),
                    expect.objectContaining({ source: 'image', value: 'height' })
                ])
            );
        });

        it('includes metadata fields of supported types with metadata. prefix label', () => {
            metadataInfo.set([
                { name: 'score', type: 'float' },
                { name: 'count', type: 'integer' },
                { name: 'label', type: 'string' },
                { name: 'active', type: 'boolean' }
            ]);
            const { allSortFields } = useOrderBy({ datasetId: 'ds1' });
            const fields = get(allSortFields);

            expect(fields).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'score',
                        label: 'metadata.score',
                        is_numeric: true
                    }),
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'count',
                        label: 'metadata.count',
                        is_numeric: true
                    }),
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'label',
                        label: 'metadata.label',
                        is_numeric: false
                    }),
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'active',
                        label: 'metadata.active',
                        is_numeric: false
                    })
                ])
            );
        });

        it('excludes list and dict metadata fields', () => {
            metadataInfo.set([
                { name: 'tags', type: 'list' },
                { name: 'nested', type: 'dict' },
                { name: 'score', type: 'float' }
            ]);
            const { allSortFields } = useOrderBy({ datasetId: 'ds1' });
            const fields = get(allSortFields);

            expect(fields.map((f) => ('value' in f ? f.value : null))).not.toContain('tags');
            expect(fields.map((f) => ('value' in f ? f.value : null))).not.toContain('nested');
        });

        it('includes evaluation metric fields with run_name_metric_name label', () => {
            metricsInfo.set({
                data: [
                    {
                        run_name: 'run1',
                        metrics: [
                            { metric_name: 'precision', min_value: 0, max_value: 1 },
                            { metric_name: 'recall', min_value: 0, max_value: 1 }
                        ]
                    }
                ]
            });
            const { allSortFields } = useOrderBy({ datasetId: 'ds1' });
            const fields = get(allSortFields);

            expect(fields).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        source: 'evaluation_metric',
                        evaluation_run_name: 'run1',
                        metric_name: 'precision',
                        label: 'run1_precision'
                    }),
                    expect.objectContaining({
                        source: 'evaluation_metric',
                        evaluation_run_name: 'run1',
                        metric_name: 'recall',
                        label: 'run1_recall'
                    })
                ])
            );
        });

        it('updates reactively when metadataInfo changes', () => {
            const { allSortFields } = useOrderBy({ datasetId: 'ds1' });

            expect(
                get(allSortFields).find((f) => 'value' in f && f.value === 'brightness')
            ).toBeUndefined();

            metadataInfo.set([{ name: 'brightness', type: 'float' }]);

            expect(
                get(allSortFields).find((f) => 'value' in f && f.value === 'brightness')
            ).toBeDefined();
        });
    });

    describe('selectedDirection', () => {
        it('returns ASC when no sort is active', () => {
            const { selectedDirection } = useOrderBy({ datasetId: 'ds1' });
            expect(get(selectedDirection)).toBe(SortDirection.ASC);
        });

        it('returns the direction of the active sort', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.DESC,
                    is_numeric: false
                }
            ]);
            const { selectedDirection } = useOrderBy({ datasetId: 'ds1' });
            expect(get(selectedDirection)).toBe(SortDirection.DESC);
        });
    });

    describe('selectedLabel', () => {
        it('returns null when no sort is active', () => {
            const { selectedLabel } = useOrderBy({ datasetId: 'ds1' });
            expect(get(selectedLabel)).toBeNull();
        });

        it('returns the label for an active image sort field', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.ASC,
                    is_numeric: false
                }
            ]);
            const { selectedLabel } = useOrderBy({ datasetId: 'ds1' });
            expect(get(selectedLabel)).toBe('file name');
        });

        it('returns the metadata label when a metadata field is active', () => {
            metadataInfo.set([{ name: 'brightness', type: 'float' }]);
            imageSortBy.set([
                {
                    source: 'metadata',
                    field_name: 'brightness',
                    direction: SortDirection.ASC,
                    is_numeric: true
                }
            ]);
            const { selectedLabel } = useOrderBy({ datasetId: 'ds1' });
            expect(get(selectedLabel)).toBe('metadata.brightness');
        });

        it('returns run_name_metric_name when an evaluation metric is active', () => {
            imageSortBy.set([
                {
                    source: 'evaluation_metric',
                    evaluation_run_name: 'run1',
                    metric_name: 'precision',
                    direction: SortDirection.ASC
                }
            ]);
            const { selectedLabel } = useOrderBy({ datasetId: 'ds1' });
            expect(get(selectedLabel)).toBe('run1_precision');
        });
    });

    describe('isFieldSelected', () => {
        it('returns false for any field when no sort is active', () => {
            const { isFieldSelected } = useOrderBy({ datasetId: 'ds1' });
            const check = get(isFieldSelected);

            expect(check({ source: 'image', value: 'file_name', label: 'file name' })).toBe(false);
        });

        it('returns true for the matching image field', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'width',
                    direction: SortDirection.ASC,
                    is_numeric: false
                }
            ]);
            const { isFieldSelected } = useOrderBy({ datasetId: 'ds1' });
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
            const { isFieldSelected } = useOrderBy({ datasetId: 'ds1' });
            const check = get(isFieldSelected);

            expect(
                check({
                    source: 'evaluation_metric',
                    evaluation_run_name: 'run1',
                    metric_name: 'precision',
                    label: 'run1_precision'
                })
            ).toBe(true);
            expect(
                check({
                    source: 'evaluation_metric',
                    evaluation_run_name: 'run1',
                    metric_name: 'recall',
                    label: 'run1_recall'
                })
            ).toBe(false);
        });

        it('updates reactively when imageSortBy changes', () => {
            const { isFieldSelected } = useOrderBy({ datasetId: 'ds1' });
            const field = { source: 'image' as const, value: 'width', label: 'width' };

            expect(get(isFieldSelected)(field)).toBe(false);

            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'width',
                    direction: SortDirection.ASC,
                    is_numeric: false
                }
            ]);

            expect(get(isFieldSelected)(field)).toBe(true);
        });
    });

    describe('handleFieldClick', () => {
        it('selects an image field with ASC direction by default', () => {
            const { handleFieldClick } = useOrderBy({ datasetId: 'ds1' });

            handleFieldClick({ source: 'image', value: 'file_name', label: 'file name' });

            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.ASC,
                    is_numeric: false
                }
            ]);
        });

        it('deselects the field when clicking the already selected field', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.ASC,
                    is_numeric: false
                }
            ]);
            const { handleFieldClick } = useOrderBy({ datasetId: 'ds1' });

            handleFieldClick({ source: 'image', value: 'file_name', label: 'file name' });

            expect(updateSortBy).toHaveBeenCalledWith(null);
        });

        it('switches to a different field while preserving the current direction', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.DESC,
                    is_numeric: false
                }
            ]);
            const { handleFieldClick } = useOrderBy({ datasetId: 'ds1' });

            handleFieldClick({ source: 'image', value: 'width', label: 'width' });

            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'image',
                    field_name: 'width',
                    direction: SortDirection.DESC,
                    is_numeric: false
                }
            ]);
        });

        it('sets is_numeric true for numeric metadata fields', () => {
            metadataInfo.set([{ name: 'score', type: 'float' }]);
            const { handleFieldClick } = useOrderBy({ datasetId: 'ds1' });

            handleFieldClick({
                source: 'metadata',
                value: 'score',
                label: 'metadata.score',
                is_numeric: true
            });

            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'metadata',
                    field_name: 'score',
                    direction: SortDirection.ASC,
                    is_numeric: true
                }
            ]);
        });

        it('selects an evaluation metric field', () => {
            const { handleFieldClick } = useOrderBy({ datasetId: 'ds1' });

            handleFieldClick({
                source: 'evaluation_metric',
                evaluation_run_name: 'run1',
                metric_name: 'precision',
                label: 'run1_precision'
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
            const { toggleDirection } = useOrderBy({ datasetId: 'ds1' });

            toggleDirection();

            expect(updateSortBy).not.toHaveBeenCalled();
        });

        it('toggles direction for an image field', () => {
            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.ASC,
                    is_numeric: false
                }
            ]);
            const { toggleDirection } = useOrderBy({ datasetId: 'ds1' });

            toggleDirection();
            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.DESC,
                    is_numeric: false
                }
            ]);

            imageSortBy.set([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.DESC,
                    is_numeric: false
                }
            ]);
            toggleDirection();
            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'image',
                    field_name: 'file_name',
                    direction: SortDirection.ASC,
                    is_numeric: false
                }
            ]);
        });

        it('preserves is_numeric when toggling direction on a metadata field', () => {
            imageSortBy.set([
                {
                    source: 'metadata',
                    field_name: 'score',
                    direction: SortDirection.ASC,
                    is_numeric: true
                }
            ]);
            const { toggleDirection } = useOrderBy({ datasetId: 'ds1' });

            toggleDirection();

            expect(updateSortBy).toHaveBeenCalledWith([
                {
                    source: 'metadata',
                    field_name: 'score',
                    direction: SortDirection.DESC,
                    is_numeric: true
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
            const { toggleDirection } = useOrderBy({ datasetId: 'ds1' });

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
