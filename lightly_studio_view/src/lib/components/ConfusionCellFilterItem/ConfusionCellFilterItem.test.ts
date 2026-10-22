import { render, screen, within } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ConfusionCellFilterItem from './ConfusionCellFilterItem.svelte';
import type { ImagesInfiniteParams } from '$lib/hooks/useImagesInfinite/useImagesInfinite';

const filterParams = writable<ImagesInfiniteParams>({} as ImagesInfiniteParams);
const updateConfusionCell = vi.fn();
const filtersMock = { filterParams, updateConfusionCell };

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: vi.fn(() => filtersMock)
}));

const normalParamsWithCell = (
    gt_label: string | null,
    pred_label: string | null
): ImagesInfiniteParams => ({
    collection_id: 'col-1',
    mode: 'normal',
    filters: {
        confusion_cell: {
            evaluation_run_id: 'run-1',
            gt_label,
            pred_label
        }
    }
});

describe('ConfusionCellFilterItem', () => {
    beforeEach(() => {
        updateConfusionCell.mockClear();
        filterParams.set({} as ImagesInfiniteParams);
    });

    it('renders nothing when there is no confusion cell in the filter params', () => {
        filterParams.set({ collection_id: 'col-1', mode: 'normal', filters: {} });

        render(ConfusionCellFilterItem);

        expect(screen.queryByTestId('confusion-cell-filter-item-chip')).not.toBeInTheDocument();
    });

    it('renders separate ground truth and prediction fields for a non-diagonal cell', () => {
        filterParams.set(normalParamsWithCell('cat', 'dog'));

        render(ConfusionCellFilterItem);

        expect(screen.getByTestId('confusion-cell-filter-item-chip')).toBeInTheDocument();
        expect(screen.getByText('Confusion Matrix')).toBeInTheDocument();
        expect(screen.getByText('Ground truth')).toBeInTheDocument();
        expect(screen.getByText('Prediction')).toBeInTheDocument();
        expect(screen.getByText('cat')).toBeInTheDocument();
        expect(screen.getByText('dog')).toBeInTheDocument();
    });

    it('renders a diagonal cell without implying confusion', () => {
        filterParams.set(normalParamsWithCell('cat', 'cat'));

        render(ConfusionCellFilterItem);

        expect(screen.getByTestId('confusion-cell-filter-item-chip')).toBeInTheDocument();
        expect(screen.getAllByText('cat')).toHaveLength(2);
    });

    it('shows missing ground truth for the false-positive bucket', () => {
        filterParams.set(normalParamsWithCell(null, 'truck'));

        render(ConfusionCellFilterItem);

        expect(screen.getByTestId('confusion-cell-filter-item-chip')).toBeInTheDocument();
        expect(screen.getByRole('emphasis')).toHaveTextContent('No ground truth');
        expect(screen.getByText('truck')).toBeInTheDocument();
    });

    it('shows a missing prediction for the false-negative bucket', () => {
        filterParams.set(normalParamsWithCell('car', null));

        render(ConfusionCellFilterItem);

        expect(screen.getByTestId('confusion-cell-filter-item-chip')).toBeInTheDocument();
        expect(screen.getByText('car')).toBeInTheDocument();
        expect(screen.getByRole('emphasis')).toHaveTextContent('No prediction');
    });

    it('keeps full class names visible and updates when another cell is selected', async () => {
        const groundTruth = 'German shepherd with a very long annotation class name';
        const prediction = 'Belgian_shepherd_with_a_very_long_unbroken_annotation_class_name';
        filterParams.set(normalParamsWithCell(groundTruth, prediction));

        render(ConfusionCellFilterItem);

        expect(screen.getByText(groundTruth)).toBeVisible();
        expect(screen.getByText(prediction)).toBeVisible();

        filterParams.set(normalParamsWithCell('cat', 'dog'));

        expect(await screen.findByText('dog')).toBeVisible();
        expect(screen.getByText('cat')).toBeVisible();
        expect(screen.queryByText(groundTruth)).not.toBeInTheDocument();
    });

    it('clears the confusion cell when the checkbox is toggled off', async () => {
        filterParams.set(normalParamsWithCell('cat', 'dog'));

        render(ConfusionCellFilterItem);

        const chip = screen.getByTestId('confusion-cell-filter-item-chip');
        const checkbox = within(chip).getByRole('checkbox', { name: 'Confusion cell filter' });
        checkbox.click();

        expect(updateConfusionCell).toHaveBeenCalledWith(null);
    });

    it('clears the confusion cell when the clear button is clicked', () => {
        filterParams.set(normalParamsWithCell('cat', 'dog'));

        render(ConfusionCellFilterItem);

        const clearButton = screen.getByRole('button', { name: 'Clear confusion matrix filter' });
        clearButton.click();

        expect(updateConfusionCell).toHaveBeenCalledWith(null);
    });
});
