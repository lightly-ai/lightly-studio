import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PlotPanelLegend from './PlotPanelLegend.svelte';
import { FILTERED_COLOR, NOT_FILTERED_COLOR } from './plotColorUtils';
import { getColorByLabel } from '$lib/utils';

describe('PlotPanelLegend', () => {
    it('renders the fixed entries and the custom legend list', () => {
        render(PlotPanelLegend, {
            categoryColors: [NOT_FILTERED_COLOR, FILTERED_COLOR, 'hsl(0, 70%, 55%)'],
            includedLabel: 'No category',
            legendEntries: [
                { cat: 2, label: 'metadata.split: train', color: 'hsl(0, 70%, 55%)', hidden: false }
            ]
        });

        // The excluded row uses its default label; the included row uses the passed-in label.
        expect(screen.getByTestId('plot-legend')).toHaveTextContent('Excluded by filters');
        expect(screen.getByTestId('plot-legend')).toHaveTextContent('No category');
        expect(screen.getByRole('button', { name: 'metadata.split: train' })).toBeInTheDocument();
    });

    it('defaults to the "Included by filters" label when none is passed', () => {
        render(PlotPanelLegend, {
            categoryColors: [NOT_FILTERED_COLOR, FILTERED_COLOR]
        });

        expect(screen.getByTestId('plot-legend')).toHaveTextContent('Excluded by filters');
        expect(screen.getByTestId('plot-legend')).toHaveTextContent('Included by filters');
    });

    it('calls the single-click handler for custom legend entries', async () => {
        const onToggleCategory = vi.fn();

        render(PlotPanelLegend, {
            categoryColors: [NOT_FILTERED_COLOR, FILTERED_COLOR, 'hsl(0, 70%, 55%)'],
            legendEntries: [{ cat: 2, label: 'Train', color: 'hsl(0, 70%, 55%)', hidden: false }],
            onToggleCategory
        });

        await fireEvent.click(screen.getByTestId('plot-legend-entry-2'));

        expect(onToggleCategory).toHaveBeenCalledWith(2);
    });

    it('calls the double-click handler for custom legend entries', async () => {
        const onDoubleClickCategory = vi.fn();

        render(PlotPanelLegend, {
            categoryColors: [NOT_FILTERED_COLOR, FILTERED_COLOR, 'hsl(0, 70%, 55%)'],
            legendEntries: [{ cat: 2, label: 'Train', color: 'hsl(0, 70%, 55%)', hidden: false }],
            onDoubleClickCategory
        });

        await fireEvent.dblClick(screen.getByTestId('plot-legend-entry-2'));

        expect(onDoubleClickCategory).toHaveBeenCalledWith(2);
    });

    it('renders tag legend entries with getColorByLabel colors', () => {
        const reviewBatch1Color = getColorByLabel('review-batch-1').color;
        const reviewBatch2Color = getColorByLabel('review-batch-2').color;

        render(PlotPanelLegend, {
            categoryColors: [
                NOT_FILTERED_COLOR,
                FILTERED_COLOR,
                reviewBatch1Color,
                reviewBatch2Color
            ],
            legendEntries: [
                { cat: 2, label: 'review-batch-1', color: reviewBatch1Color, hidden: false },
                { cat: 3, label: 'review-batch-2', color: reviewBatch2Color, hidden: false }
            ]
        });

        expect(screen.getByRole('button', { name: 'review-batch-1' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'review-batch-2' })).toBeInTheDocument();
    });
});
