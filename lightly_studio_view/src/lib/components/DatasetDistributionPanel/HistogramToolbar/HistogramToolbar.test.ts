import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import HistogramToolbar from './HistogramToolbar.svelte';
import type { HistogramData } from '$lib/components/Histogram';
import { HISTOGRAM_BIN_COUNT_ITEMS } from '../types';
import type { SelectItem } from '$lib/components/Select';

const histogram: HistogramData = { binEdges: [0, 0.5, 1], counts: [30, 70] };

const binCountItems: SelectItem[] = HISTOGRAM_BIN_COUNT_ITEMS.map((count) => ({
    value: String(count),
    label: `${count} bins`
}));

const defaultProps = {
    histogram,
    histogramTotal: 100,
    valueNoun: 'annotations',
    histogramBinCount: 20,
    binCountItems,
    onHistogramBinCountChange: vi.fn(),
    onExpand: vi.fn()
};

describe('HistogramToolbar', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
    });

    afterEach(() => {
        document.body.innerHTML = '';
        document.body.style.pointerEvents = '';
    });

    it('renders the summary with total count, bin count, and range', () => {
        render(HistogramToolbar, { props: defaultProps });

        expect(screen.getByTestId('dataset-distribution-histogram-summary')).toHaveTextContent(
            '100 annotations · 2 bins · 0–1'
        );
    });

    it('uses the singular "bin" when there is only one bin', () => {
        render(HistogramToolbar, {
            props: {
                ...defaultProps,
                histogram: { binEdges: [0, 1], counts: [50] },
                histogramTotal: 50
            }
        });

        expect(screen.getByTestId('dataset-distribution-histogram-summary')).toHaveTextContent(
            '1 bin ·'
        );
    });

    it('shows the bin-count selector with the applied bin count', () => {
        render(HistogramToolbar, { props: { ...defaultProps, histogramBinCount: 50 } });

        expect(screen.getByTestId('dataset-distribution-bin-count')).toHaveTextContent('50 bins');
    });

    it('calls onHistogramBinCountChange with the selected count', async () => {
        const onHistogramBinCountChange = vi.fn();
        const user = userEvent.setup();
        render(HistogramToolbar, { props: { ...defaultProps, onHistogramBinCountChange } });

        await user.click(screen.getByTestId('dataset-distribution-bin-count'));
        const option = await waitFor(() => screen.getByRole('option', { name: '10 bins' }));
        await user.click(option);

        expect(onHistogramBinCountChange).toHaveBeenCalledWith(10);
    });

    it('calls onExpand when the expand button is clicked', async () => {
        const onExpand = vi.fn();
        const user = userEvent.setup();
        render(HistogramToolbar, { props: { ...defaultProps, onExpand } });

        await user.click(screen.getByTestId('dataset-distribution-histogram-expand'));

        expect(onExpand).toHaveBeenCalledOnce();
    });

    it('uses the provided valueNoun in the summary', () => {
        render(HistogramToolbar, { props: { ...defaultProps, valueNoun: 'samples' } });

        expect(screen.getByTestId('dataset-distribution-histogram-summary')).toHaveTextContent(
            '100 samples ·'
        );
    });

    it('switches to percentage mode and updates the summary', async () => {
        const onValueModeChange = vi.fn();
        const user = userEvent.setup();
        render(HistogramToolbar, {
            props: {
                ...defaultProps,
                valueMode: 'percentage',
                onValueModeChange
            }
        });

        expect(screen.getByTestId('dataset-distribution-histogram-summary')).toHaveTextContent(
            '100% of 100 annotations'
        );
        await user.click(screen.getByTestId('dataset-distribution-histogram-value-mode'));
        await user.click(await screen.findByRole('option', { name: 'Number' }));
        expect(onValueModeChange).toHaveBeenCalledWith('number');
    });
});
