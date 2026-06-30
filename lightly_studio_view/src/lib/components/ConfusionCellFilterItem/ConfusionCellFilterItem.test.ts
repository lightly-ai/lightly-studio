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

    it('renders the chip with the GT and Pred labels for a non-diagonal cell', () => {
        filterParams.set(normalParamsWithCell('cat', 'dog'));

        render(ConfusionCellFilterItem);

        expect(screen.getByTestId('confusion-cell-filter-item-chip')).toBeInTheDocument();
        expect(screen.getByText('Confusion Matrix')).toBeInTheDocument();
        expect(screen.getByText('GT: cat → Pred: dog')).toBeInTheDocument();
    });

    it('renders a diagonal cell without implying confusion', () => {
        filterParams.set(normalParamsWithCell('cat', 'cat'));

        render(ConfusionCellFilterItem);

        expect(screen.getByTestId('confusion-cell-filter-item-chip')).toBeInTheDocument();
        expect(screen.getByText('GT: cat → Pred: cat')).toBeInTheDocument();
    });

    it('labels the false-positive bucket (null gt_label) as "Predicted only: <class>"', () => {
        filterParams.set(normalParamsWithCell(null, 'truck'));

        render(ConfusionCellFilterItem);

        expect(screen.getByTestId('confusion-cell-filter-item-chip')).toBeInTheDocument();
        expect(screen.getByText('Predicted only: truck')).toBeInTheDocument();
    });

    it('labels the false-negative bucket (null pred_label) as "Ground truth only: <class>"', () => {
        filterParams.set(normalParamsWithCell('car', null));

        render(ConfusionCellFilterItem);

        expect(screen.getByTestId('confusion-cell-filter-item-chip')).toBeInTheDocument();
        expect(screen.getByText('Ground truth only: car')).toBeInTheDocument();
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

        const clearButton = screen.getByRole('button', { name: /clear gt: cat → pred: dog/i });
        clearButton.click();

        expect(updateConfusionCell).toHaveBeenCalledWith(null);
    });
});
