import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PlotSelectionBanner from './PlotSelectionBanner.svelte';

describe('PlotSelectionBanner', () => {
    it('renders the active selection count and clear action', () => {
        render(PlotSelectionBanner, {
            props: {
                selectionCount: 3,
                showPlot: false,
                onClear: vi.fn()
            }
        });

        expect(screen.getByTestId('plot-selection-banner')).toBeInTheDocument();
        expect(screen.getByText('Plot selection active: 3 samples')).toBeInTheDocument();
        expect(screen.getByTestId('plot-selection-banner-clear')).toBeInTheDocument();
    });

    it('shows the plot button only while the plot is hidden', () => {
        const { unmount } = render(PlotSelectionBanner, {
            props: {
                selectionCount: 2,
                showPlot: false,
                onClear: vi.fn(),
                onShowPlot: vi.fn()
            }
        });

        expect(screen.getByTestId('plot-selection-banner-show-plot')).toBeInTheDocument();

        unmount();

        render(PlotSelectionBanner, {
            props: {
            selectionCount: 2,
            showPlot: true,
            onClear: vi.fn(),
            onShowPlot: vi.fn()
            }
        });

        expect(screen.queryByTestId('plot-selection-banner-show-plot')).not.toBeInTheDocument();
    });

    it('calls the action handlers when buttons are pressed', async () => {
        const onClear = vi.fn();
        const onShowPlot = vi.fn();
        const onToggleSelectionApplied = vi.fn();

        render(PlotSelectionBanner, {
            props: {
                selectionCount: 1,
                showPlot: false,
                onClear,
                onShowPlot,
                onToggleSelectionApplied,
                itemLabel: 'video'
            }
        });

        await fireEvent.click(screen.getByTestId('plot-selection-banner-toggle-apply'));
        await fireEvent.click(screen.getByTestId('plot-selection-banner-show-plot'));
        await fireEvent.click(screen.getByTestId('plot-selection-banner-clear'));

        expect(screen.getByText('Plot selection active: 1 video')).toBeInTheDocument();
        expect(onToggleSelectionApplied).toHaveBeenCalledTimes(1);
        expect(onShowPlot).toHaveBeenCalledTimes(1);
        expect(onClear).toHaveBeenCalledTimes(1);
    });

    it('renders paused selection state text and action label', () => {
        render(PlotSelectionBanner, {
            props: {
                selectionCount: 5,
                selectionApplied: false,
                showPlot: false,
                onClear: vi.fn()
            }
        });

        expect(screen.getByText('Selection is saved but not applied to the grid.')).toBeInTheDocument();
        expect(screen.getByText('Re-enable selection')).toBeInTheDocument();
    });
});
