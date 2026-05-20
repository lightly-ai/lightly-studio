import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PlotPanelLegend from './PlotPanelLegend.svelte';
import { FILTERED_COLOR, NOT_FILTERED_COLOR } from './plotColorUtils';

describe('PlotPanelLegend', () => {
    it('renders the fixed entries and the custom legend list', () => {
        render(PlotPanelLegend, {
            categoryColors: [NOT_FILTERED_COLOR, FILTERED_COLOR, 'hsl(0, 70%, 55%)'],
            filteredLabel: 'Unassigned',
            legendEntries: [
                { cat: 2, label: 'metadata.split: train', color: 'hsl(0, 70%, 55%)', hidden: false }
            ]
        });

        expect(screen.getByTestId('plot-legend')).toHaveTextContent('Not Filtered');
        expect(screen.getByTestId('plot-legend')).toHaveTextContent('Unassigned');
        expect(screen.getByRole('button', { name: 'metadata.split: train' })).toBeInTheDocument();
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
});
