import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PlotPanelLegend from './PlotPanelLegend.svelte';
import { FILTERED_COLOR, HIDDEN_COLOR, NOT_FILTERED_COLOR } from './plotColorUtils';
import { getColorByLabel } from '$lib/utils';

describe('PlotPanelLegend', () => {
    it('renders the fixed entries and the custom legend list', () => {
        render(PlotPanelLegend, {
            categoryColors: [HIDDEN_COLOR, NOT_FILTERED_COLOR, FILTERED_COLOR, 'rgb(255, 0, 136)'],
            includedLabel: 'No category',
            legendEntries: [
                { cat: 3, label: 'metadata.split: train', color: 'rgb(255, 0, 136)', hidden: false }
            ]
        });

        // The excluded row uses its default label; the included row uses the passed-in label.
        expect(screen.getByTestId('plot-legend')).toHaveTextContent('Excluded by filters');
        expect(screen.getByTestId('plot-legend')).toHaveTextContent('No category');
        expect(screen.getByRole('button', { name: 'metadata.split: train' })).toBeInTheDocument();
    });

    it('defaults to the "Included by filters" label when none is passed', () => {
        render(PlotPanelLegend, {
            categoryColors: [HIDDEN_COLOR, NOT_FILTERED_COLOR, FILTERED_COLOR]
        });

        expect(screen.getByTestId('plot-legend')).toHaveTextContent('Excluded by filters');
        expect(screen.getByTestId('plot-legend')).toHaveTextContent('Included by filters');
    });

    it('calls the single-click handler for custom legend entries', async () => {
        const onToggleCategory = vi.fn();

        render(PlotPanelLegend, {
            categoryColors: [HIDDEN_COLOR, NOT_FILTERED_COLOR, FILTERED_COLOR, 'rgb(255, 0, 136)'],
            legendEntries: [{ cat: 3, label: 'Train', color: 'rgb(255, 0, 136)', hidden: false }],
            onToggleCategory
        });

        await fireEvent.click(screen.getByTestId('plot-legend-entry-3'));

        expect(onToggleCategory).toHaveBeenCalledWith(3);
    });

    it('calls the double-click handler for custom legend entries', async () => {
        const onDoubleClickCategory = vi.fn();

        render(PlotPanelLegend, {
            categoryColors: [HIDDEN_COLOR, NOT_FILTERED_COLOR, FILTERED_COLOR, 'rgb(255, 0, 136)'],
            legendEntries: [{ cat: 3, label: 'Train', color: 'rgb(255, 0, 136)', hidden: false }],
            onDoubleClickCategory
        });

        await fireEvent.dblClick(screen.getByTestId('plot-legend-entry-3'));

        expect(onDoubleClickCategory).toHaveBeenCalledWith(3);
    });

    it('toggles the reserved rows on single click', async () => {
        const onToggleCategory = vi.fn();

        render(PlotPanelLegend, {
            categoryColors: [HIDDEN_COLOR, NOT_FILTERED_COLOR, FILTERED_COLOR],
            onToggleCategory
        });

        // EXCLUDED_BY_FILTERS_CATEGORY === 1, INCLUDED_BY_FILTERS_CATEGORY === 2.
        await fireEvent.click(screen.getByTestId('plot-legend-entry-1'));
        expect(onToggleCategory).toHaveBeenCalledWith(1);

        await fireEvent.click(screen.getByTestId('plot-legend-entry-2'));
        expect(onToggleCategory).toHaveBeenCalledWith(2);
    });

    it('does not isolate the reserved rows on double click', async () => {
        const onDoubleClickCategory = vi.fn();

        render(PlotPanelLegend, {
            categoryColors: [HIDDEN_COLOR, NOT_FILTERED_COLOR, FILTERED_COLOR],
            onDoubleClickCategory
        });

        await fireEvent.dblClick(screen.getByTestId('plot-legend-entry-1'));
        await fireEvent.dblClick(screen.getByTestId('plot-legend-entry-2'));

        expect(onDoubleClickCategory).not.toHaveBeenCalled();
    });

    it('dims the reserved rows when hidden', () => {
        render(PlotPanelLegend, {
            categoryColors: [HIDDEN_COLOR, NOT_FILTERED_COLOR, FILTERED_COLOR],
            excludedHidden: true,
            includedHidden: false
        });

        const excludedRow = screen.getByTestId('plot-legend-entry-1');
        const includedRow = screen.getByTestId('plot-legend-entry-2');

        expect(excludedRow).toHaveAttribute('aria-pressed', 'true');
        expect(excludedRow.className).toContain('opacity-40');
        expect(includedRow).toHaveAttribute('aria-pressed', 'false');
        expect(includedRow.className).not.toContain('opacity-40');
    });

    describe('scroll fade cues', () => {
        // jsdom does no layout, so scroll metrics must be stubbed before firing scroll.
        const setScrollMetrics = (
            element: HTMLElement,
            { scrollTop, scrollHeight, clientHeight }: Record<string, number>
        ) => {
            Object.defineProperty(element, 'scrollHeight', {
                value: scrollHeight,
                configurable: true
            });
            Object.defineProperty(element, 'clientHeight', {
                value: clientHeight,
                configurable: true
            });
            element.scrollTop = scrollTop;
        };

        const renderScrollContainer = () => {
            render(PlotPanelLegend, {
                categoryColors: [HIDDEN_COLOR, NOT_FILTERED_COLOR, FILTERED_COLOR]
            });
            return screen.getByTestId('plot-legend-scroll');
        };

        it('shows no fade when the content fits', async () => {
            const container = renderScrollContainer();

            setScrollMetrics(container, { scrollTop: 0, scrollHeight: 100, clientHeight: 100 });
            await fireEvent.scroll(container);

            expect(container.className).not.toContain('legend-fade');
        });

        it('fades the bottom when scrolled to the top of overflowing content', async () => {
            const container = renderScrollContainer();

            setScrollMetrics(container, { scrollTop: 0, scrollHeight: 200, clientHeight: 100 });
            await fireEvent.scroll(container);

            expect(container.className).toContain('legend-fade-bottom');
            expect(container.className).not.toContain('legend-fade-top');
            expect(container.className).not.toContain('legend-fade-both');
        });

        it('fades both edges when scrolled to the middle', async () => {
            const container = renderScrollContainer();

            setScrollMetrics(container, { scrollTop: 50, scrollHeight: 200, clientHeight: 100 });
            await fireEvent.scroll(container);

            expect(container.className).toContain('legend-fade-both');
        });

        it('fades the top when scrolled to the bottom', async () => {
            const container = renderScrollContainer();

            setScrollMetrics(container, { scrollTop: 100, scrollHeight: 200, clientHeight: 100 });
            await fireEvent.scroll(container);

            expect(container.className).toContain('legend-fade-top');
            expect(container.className).not.toContain('legend-fade-bottom');
            expect(container.className).not.toContain('legend-fade-both');
        });
    });

    it('renders tag legend entries with getColorByLabel colors', () => {
        const reviewBatch1Color = getColorByLabel('review-batch-1').color;
        const reviewBatch2Color = getColorByLabel('review-batch-2').color;

        render(PlotPanelLegend, {
            categoryColors: [
                HIDDEN_COLOR,
                NOT_FILTERED_COLOR,
                FILTERED_COLOR,
                reviewBatch1Color,
                reviewBatch2Color
            ],
            legendEntries: [
                { cat: 3, label: 'review-batch-1', color: reviewBatch1Color, hidden: false },
                { cat: 4, label: 'review-batch-2', color: reviewBatch2Color, hidden: false }
            ]
        });

        expect(screen.getByRole('button', { name: 'review-batch-1' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'review-batch-2' })).toBeInTheDocument();
    });
});
