import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type { MetadataInfoView } from '$lib/api/lightly_studio_local';
import type { EvaluationRunMetricsInfoView } from '$lib/api/lightly_studio_local/types.gen';
import OrderBy from './OrderBy.svelte';
import type { SortExpr } from '$lib/hooks/useImagesInfinite/types';

const mocks = vi.hoisted(() => ({
    imageSortByValue: null as SortExpr[] | null,
    updateSortBy: vi.fn(),
    metadataInfoValue: [] as MetadataInfoView[],
    metricsProxy: { data: null as EvaluationRunMetricsInfoView[] | null, dataUpdatedAt: 0 }
}));

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({
        imageSortBy: readable(mocks.imageSortByValue),
        updateSortBy: mocks.updateSortBy
    })
}));

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: () => ({
        metadataInfo: readable(mocks.metadataInfoValue)
    })
}));

vi.mock('$lib/hooks/useEvaluationSampleMetricsInfo/useEvaluationSampleMetricsInfo', () => ({
    useEvaluationSampleMetricsInfo: () => mocks.metricsProxy
}));

describe('OrderBy', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.imageSortByValue = null;
        mocks.metadataInfoValue = [];
        mocks.metricsProxy.data = null;
        mocks.metricsProxy.dataUpdatedAt = 0;
    });

    it('shows the default sort field when no explicit field is selected', () => {
        render(OrderBy, { props: { datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('file path');
    });

    it('shows the selected field label in the trigger', () => {
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC,
                is_numeric: false
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('file name');
    });

    it('toggles the default sort direction from the arrow button', async () => {
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'file_path_abs',
                direction: SortDirection.DESC,
                is_numeric: false
            }
        ]);
    });

    it('selects a field and calls updateSortBy with asc direction by default', async () => {
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-file_name'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC,
                is_numeric: false
            }
        ]);
    });

    it('does not update sorting when clicking the already selected item', async () => {
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC,
                is_numeric: false
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-file_name'));

        expect(mocks.updateSortBy).not.toHaveBeenCalled();
    });

    it('switches to a different field while preserving the current direction', async () => {
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.DESC,
                is_numeric: false
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-width'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'width',
                direction: SortDirection.DESC,
                is_numeric: false
            }
        ]);
    });

    it('toggles direction from asc to desc', async () => {
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC,
                is_numeric: false
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.DESC,
                is_numeric: false
            }
        ]);
    });

    it('toggles direction from desc to asc', async () => {
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.DESC,
                is_numeric: false
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC,
                is_numeric: false
            }
        ]);
    });

    it('sets descending direction for the default sort', async () => {
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'file_path_abs',
                direction: SortDirection.DESC,
                is_numeric: false
            }
        ]);
    });

    it('lists all sort fields in the dropdown', async () => {
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.getByTestId('sort-field-file_name')).toHaveTextContent('file name');
        expect(screen.getByTestId('sort-field-file_path_abs')).toHaveTextContent('file path');
        expect(screen.getByTestId('sort-field-created_at')).toHaveTextContent('created at');
        expect(screen.getByTestId('sort-field-width')).toHaveTextContent('width');
        expect(screen.getByTestId('sort-field-height')).toHaveTextContent('height');
    });

    it('lists metadata fields in the dropdown as metadata.[field]', async () => {
        mocks.metadataInfoValue = [
            { name: 'brightness', type: 'float' },
            { name: 'count', type: 'integer' },
            { name: 'label', type: 'string' },
            { name: 'active', type: 'boolean' }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.getByTestId('sort-field-brightness')).toHaveTextContent(
            'metadata.brightness'
        );
        expect(screen.getByTestId('sort-field-count')).toHaveTextContent('metadata.count');
        expect(screen.getByTestId('sort-field-label')).toHaveTextContent('metadata.label');
        expect(screen.getByTestId('sort-field-active')).toHaveTextContent('metadata.active');
    });

    it('excludes list and dict metadata fields from the dropdown', async () => {
        mocks.metadataInfoValue = [
            { name: 'tags', type: 'list' },
            { name: 'nested', type: 'dict' },
            { name: 'score', type: 'float' }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.queryByTestId('sort-field-tags')).toBeNull();
        expect(screen.queryByTestId('sort-field-nested')).toBeNull();
        expect(screen.getByTestId('sort-field-score')).toHaveTextContent('metadata.score');
    });

    it('selects a numeric metadata field with is_numeric true', async () => {
        mocks.metadataInfoValue = [{ name: 'score', type: 'float' }];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-score'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'metadata',
                field_name: 'score',
                direction: SortDirection.ASC,
                is_numeric: true
            }
        ]);
    });

    it('selects a string metadata field with is_numeric false', async () => {
        mocks.metadataInfoValue = [{ name: 'category', type: 'string' }];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-category'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'metadata',
                field_name: 'category',
                direction: SortDirection.ASC,
                is_numeric: false
            }
        ]);
    });

    it('shows metadata.[field] label in the trigger when a metadata field is selected', () => {
        mocks.metadataInfoValue = [{ name: 'brightness', type: 'float' }];
        mocks.imageSortByValue = [
            {
                source: 'metadata',
                field_name: 'brightness',
                direction: SortDirection.ASC,
                is_numeric: true
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('metadata.brightness');
    });

    it('preserves is_numeric when toggling direction on a metadata field', async () => {
        mocks.metadataInfoValue = [{ name: 'score', type: 'float' }];
        mocks.imageSortByValue = [
            {
                source: 'metadata',
                field_name: 'score',
                direction: SortDirection.ASC,
                is_numeric: true
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'metadata',
                field_name: 'score',
                direction: SortDirection.DESC,
                is_numeric: true
            }
        ]);
    });

    it('lists evaluation metric fields in the dropdown as [run_name].[metric_name]', async () => {
        mocks.metricsProxy.data = [
            {
                run_name: 'run1',
                metrics: [
                    { metric_name: 'precision', min_value: 0, max_value: 1 },
                    { metric_name: 'recall', min_value: 0, max_value: 1 }
                ]
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.getByTestId('sort-field-run1-precision')).toHaveTextContent('run1.precision');
        expect(screen.getByTestId('sort-field-run1-recall')).toHaveTextContent('run1.recall');
    });

    it('selects an evaluation metric field', async () => {
        mocks.metricsProxy.data = [
            {
                run_name: 'run1',
                metrics: [{ metric_name: 'precision', min_value: 0, max_value: 1 }]
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-run1-precision'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'evaluation_metric',
                evaluation_run_name: 'run1',
                metric_name: 'precision',
                direction: SortDirection.ASC
            }
        ]);
    });

    it('does not update sorting when clicking the already selected evaluation metric', async () => {
        mocks.metricsProxy.data = [
            {
                run_name: 'run1',
                metrics: [{ metric_name: 'precision', min_value: 0, max_value: 1 }]
            }
        ];
        mocks.imageSortByValue = [
            {
                source: 'evaluation_metric',
                evaluation_run_name: 'run1',
                metric_name: 'precision',
                direction: SortDirection.ASC
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-run1-precision'));

        expect(mocks.updateSortBy).not.toHaveBeenCalled();
    });

    it('shows a dot-formatted label in the trigger when an evaluation metric is selected', () => {
        mocks.imageSortByValue = [
            {
                source: 'evaluation_metric',
                evaluation_run_name: 'run1',
                metric_name: 'precision',
                direction: SortDirection.ASC
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('run1.precision');
    });

    it('toggles direction for an evaluation metric field', async () => {
        mocks.imageSortByValue = [
            {
                source: 'evaluation_metric',
                evaluation_run_name: 'run1',
                metric_name: 'precision',
                direction: SortDirection.ASC
            }
        ];
        render(OrderBy, { props: { datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'evaluation_metric',
                evaluation_run_name: 'run1',
                metric_name: 'precision',
                direction: SortDirection.DESC
            }
        ]);
    });
});
