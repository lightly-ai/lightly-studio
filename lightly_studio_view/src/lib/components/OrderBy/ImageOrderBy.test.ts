import { fireEvent, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { readable } from 'svelte/store';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type { MetadataInfoView } from '$lib/api/lightly_studio_local';
import type { EvaluationRunMetricsInfoView } from '$lib/api/lightly_studio_local/types.gen';
import type { TextEmbedding } from '$lib/hooks/useGlobalStorage';
import ImageOrderBy from './ImageOrderBy.svelte';
import type { ImageSortExpr } from '$lib/hooks/useImagesInfinite/types';

const mocks = vi.hoisted(() => ({
    imageSortByValue: null as ImageSortExpr[] | null,
    updateSortBy: vi.fn(),
    metadataInfoValue: [] as MetadataInfoView[],
    metricsProxy: { data: null as EvaluationRunMetricsInfoView[] | null, dataUpdatedAt: 0 },
    textEmbeddingValue: undefined as TextEmbedding | undefined,
    capturedDatasetIdGetter: undefined as (() => string) | undefined
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
    useEvaluationSampleMetricsInfo: ({ datasetId }: { datasetId: () => string }) => {
        mocks.capturedDatasetIdGetter = datasetId;
        return mocks.metricsProxy;
    }
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        textEmbedding: readable(mocks.textEmbeddingValue)
    })
}));

describe('ImageOrderBy', () => {
    beforeAll(() => {
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
        Element.prototype.scrollIntoView = vi.fn();
    });

    beforeEach(() => {
        vi.clearAllMocks();
        mocks.imageSortByValue = null;
        mocks.metadataInfoValue = [];
        mocks.metricsProxy.data = null;
        mocks.metricsProxy.dataUpdatedAt = 0;
        mocks.textEmbeddingValue = undefined;
        mocks.capturedDatasetIdGetter = undefined;
    });

    it('shows placeholder text when no field is selected', () => {
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('Sort by');
    });

    it('shows a tooltip on hover over the sort trigger', async () => {
        const user = userEvent.setup();
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.hover(screen.getByTestId('sort-by-trigger'));

        expect(screen.getByRole('tooltip')).toHaveTextContent('Sort items by attribute');
    });

    it('shows the selected field label in the trigger', () => {
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('file name');
    });

    it('direction button is disabled when no field is selected', () => {
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-direction-button')).toBeDisabled();
    });

    it('direction button is enabled when a field is selected', () => {
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'width',
                direction: SortDirection.ASC
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-direction-button')).not.toBeDisabled();
    });

    it('shows a sort ascending tooltip on hover over the direction button', async () => {
        const user = userEvent.setup();
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.hover(screen.getByTestId('sort-direction-button'));

        expect(screen.getByRole('tooltip')).toHaveTextContent('Sort ascending');
    });

    it('shows a sort descending tooltip on hover over the direction button', async () => {
        const user = userEvent.setup();
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.DESC
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.hover(screen.getByTestId('sort-direction-button'));

        expect(screen.getByRole('tooltip')).toHaveTextContent('Sort descending');
    });

    it('selects a field and calls updateSortBy with asc direction by default', async () => {
        const user = userEvent.setup();
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.click(screen.getByTestId('sort-by-trigger'));
        await user.click(screen.getByTestId('sort-field-file_name'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC
            }
        ]);
    });

    it('deselects the field when clicking the already selected item', async () => {
        const user = userEvent.setup();
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.click(screen.getByTestId('sort-by-trigger'));
        await user.click(screen.getByTestId('sort-field-file_name'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith(null);
    });

    it('switches to a different field while preserving the current direction', async () => {
        const user = userEvent.setup();
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.DESC
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.click(screen.getByTestId('sort-by-trigger'));
        await user.click(screen.getByTestId('sort-field-width'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'width',
                direction: SortDirection.DESC
            }
        ]);
    });

    it('toggles direction from asc to desc', async () => {
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.DESC
            }
        ]);
    });

    it('toggles direction from desc to asc', async () => {
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.DESC
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC
            }
        ]);
    });

    it('does not call updateSortBy when direction button is clicked with no field selected', async () => {
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).not.toHaveBeenCalled();
    });

    it('lists all sort fields in the dropdown', async () => {
        const user = userEvent.setup();
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.getByTestId('sort-field-file_name')).toHaveTextContent('file name');
        expect(screen.getByTestId('sort-field-file_path_abs')).toHaveTextContent('file path');
        expect(screen.getByTestId('sort-field-created_at')).toHaveTextContent('created at');
        expect(screen.getByTestId('sort-field-width')).toHaveTextContent('width');
        expect(screen.getByTestId('sort-field-height')).toHaveTextContent('height');
    });

    it('lists metadata fields in the dropdown as metadata.[field]', async () => {
        const user = userEvent.setup();
        mocks.metadataInfoValue = [
            { name: 'brightness', type: 'float' },
            { name: 'count', type: 'integer' },
            { name: 'label', type: 'string' },
            { name: 'active', type: 'boolean' }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.getByTestId('sort-field-brightness')).toHaveTextContent(
            'metadata.brightness'
        );
        expect(screen.getByTestId('sort-field-count')).toHaveTextContent('metadata.count');
        expect(screen.getByTestId('sort-field-label')).toHaveTextContent('metadata.label');
        expect(screen.getByTestId('sort-field-active')).toHaveTextContent('metadata.active');
    });

    it('excludes list and dict metadata fields from the dropdown', async () => {
        const user = userEvent.setup();
        mocks.metadataInfoValue = [
            { name: 'tags', type: 'list' },
            { name: 'nested', type: 'dict' },
            { name: 'score', type: 'float' }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.queryByTestId('sort-field-tags')).toBeNull();
        expect(screen.queryByTestId('sort-field-nested')).toBeNull();
        expect(screen.getByTestId('sort-field-score')).toHaveTextContent('metadata.score');
    });

    it('selects a metadata field', async () => {
        const user = userEvent.setup();
        mocks.metadataInfoValue = [{ name: 'score', type: 'float' }];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.click(screen.getByTestId('sort-by-trigger'));
        await user.click(screen.getByTestId('sort-field-score'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'metadata',
                field_name: 'score',
                direction: SortDirection.ASC
            }
        ]);
    });

    it('shows metadata.[field] label in the trigger when a metadata field is selected', () => {
        mocks.metadataInfoValue = [{ name: 'brightness', type: 'float' }];
        mocks.imageSortByValue = [
            {
                source: 'metadata',
                field_name: 'brightness',
                direction: SortDirection.ASC
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('metadata.brightness');
    });

    it('toggles direction for a metadata field', async () => {
        mocks.metadataInfoValue = [{ name: 'score', type: 'float' }];
        mocks.imageSortByValue = [
            {
                source: 'metadata',
                field_name: 'score',
                direction: SortDirection.ASC
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'metadata',
                field_name: 'score',
                direction: SortDirection.DESC
            }
        ]);
    });

    it('lists evaluation metric fields in the dropdown as [run_name].[metric_name]', async () => {
        const user = userEvent.setup();
        mocks.metricsProxy.data = [
            {
                run_name: 'run1',
                metrics: [
                    { metric_name: 'precision', min_value: 0, max_value: 1 },
                    { metric_name: 'recall', min_value: 0, max_value: 1 }
                ]
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.getByTestId('sort-field-run1-precision')).toHaveTextContent('run1.precision');
        expect(screen.getByTestId('sort-field-run1-recall')).toHaveTextContent('run1.recall');
    });

    it('selects an evaluation metric field', async () => {
        const user = userEvent.setup();
        mocks.metricsProxy.data = [
            {
                run_name: 'run1',
                metrics: [{ metric_name: 'precision', min_value: 0, max_value: 1 }]
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.click(screen.getByTestId('sort-by-trigger'));
        await user.click(screen.getByTestId('sort-field-run1-precision'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'evaluation_metric',
                evaluation_run_name: 'run1',
                metric_name: 'precision',
                direction: SortDirection.ASC
            }
        ]);
    });

    it('deselects an evaluation metric field when clicking the already selected item', async () => {
        const user = userEvent.setup();
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
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

        await user.click(screen.getByTestId('sort-by-trigger'));
        await user.click(screen.getByTestId('sort-field-run1-precision'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith(null);
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
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('run1.precision');
    });

    it('disables the sort select when text embedding is active', () => {
        mocks.textEmbeddingValue = { embedding: [0.1, 0.2], queryText: 'dogs' };
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-by-trigger')).toBeDisabled();
    });

    it('disables the direction button when text embedding is active', () => {
        mocks.textEmbeddingValue = { embedding: [0.1, 0.2], queryText: 'dogs' };
        mocks.imageSortByValue = [
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC
            }
        ];
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-direction-button')).toBeDisabled();
    });

    it('enables the sort select when text embedding is inactive', () => {
        mocks.textEmbeddingValue = undefined;
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });
        expect(screen.getByTestId('sort-by-trigger')).not.toBeDisabled();
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
        render(ImageOrderBy, { props: { collectionId: 'col1', datasetId: 'ds1' } });

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

    it('passes a reactive datasetId getter that tracks the current prop after navigation', async () => {
        const { rerender } = render(ImageOrderBy, {
            props: { collectionId: 'col1', datasetId: 'ds1' }
        });

        expect(mocks.capturedDatasetIdGetter!()).toBe('ds1');

        await rerender({ collectionId: 'col1', datasetId: 'ds2' });

        expect(mocks.capturedDatasetIdGetter!()).toBe('ds2');
    });
});
