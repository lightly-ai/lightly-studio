import { render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import BarChart from './BarChart.svelte';
import { balanced, empty } from './fixtures';
import type { CategoryCountSeries } from './types';

const echartsMock = vi.hoisted(() => {
    let clickHandler: ((params: { dataIndex?: number }) => void) | undefined;
    const instance = {
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn((event: string, handler: (params: { dataIndex?: number }) => void) => {
            if (event === 'click') clickHandler = handler;
        })
    };
    return {
        init: vi.fn(() => instance),
        instance,
        getClickHandler: () => clickHandler
    };
});

vi.mock('echarts/core', () => ({
    init: echartsMock.init,
    use: vi.fn()
}));
vi.mock('echarts/charts', () => ({ BarChart: {} }));
vi.mock('echarts/components', () => ({
    GridComponent: {},
    LegendComponent: {},
    TooltipComponent: {}
}));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
    } as unknown as typeof ResizeObserver;
}

describe('BarChart', () => {
    it('renders the empty state when there is no data', () => {
        render(BarChart, { props: { data: empty } });
        expect(screen.getByTestId('bar-chart-empty')).toBeInTheDocument();
    });

    it('renders the default empty message when no emptyState snippet is provided', () => {
        render(BarChart, { props: { data: empty } });
        const emptyState = screen.getByTestId('bar-chart-empty');

        expect(emptyState).toHaveTextContent('No distribution data to display.');
        expect(emptyState).toHaveTextContent(
            'Add annotations or metadata to see their distribution.'
        );
        expect(screen.getByRole('link', { name: 'documentation' })).toHaveAttribute(
            'href',
            'https://docs.lightly.ai/studio/'
        );
    });

    it('renders a custom emptyState snippet instead of the default message', () => {
        const emptyState = createRawSnippet(() => ({
            render: () => '<span data-testid="custom-empty">Custom empty message</span>'
        }));
        render(BarChart, { props: { data: empty, emptyState } });
        expect(screen.getByTestId('custom-empty')).toBeInTheDocument();
        expect(screen.queryByText('No distribution data to display.')).not.toBeInTheDocument();
    });

    it('renders the chart container for non-empty data', () => {
        render(BarChart, { props: { data: balanced } });
        expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    });

    it('resolves a bar click to its category', () => {
        const onBarClick = vi.fn();
        render(BarChart, { props: { data: balanced, onBarClick } });

        const handler = echartsMock.getClickHandler();
        expect(handler).toBeDefined();
        handler?.({ dataIndex: 1 });

        expect(onBarClick).toHaveBeenCalledWith(balanced[1]);
    });

    it('ignores clicks without a data index', () => {
        const onBarClick = vi.fn();
        render(BarChart, { props: { data: balanced, onBarClick } });

        echartsMock.getClickHandler()?.({});

        expect(onBarClick).not.toHaveBeenCalled();
    });

    it('applies maxWidthPx as a max-width inline style', () => {
        render(BarChart, { props: { data: balanced, maxWidthPx: 600 } });
        expect(screen.getByTestId('bar-chart')).toHaveStyle({ 'max-width': '600px' });
    });

    it('applies maxHeightPx as height for vertical orientation', () => {
        render(BarChart, { props: { data: balanced, maxHeightPx: 400 } });
        expect(screen.getByTestId('bar-chart')).toHaveStyle({ height: '400px' });
    });

    it('applies maxHeightPx as max-height for horizontal orientation', () => {
        render(BarChart, {
            props: { data: balanced, maxHeightPx: 400, orientation: 'horizontal' }
        });
        expect(screen.getByTestId('bar-chart')).toHaveStyle({ 'max-height': '400px' });
    });

    it('adds legend height to the canvas when horizontal with grouped series', () => {
        // BAR_THICKNESS_PX=28, series.length*14=28, categoryThicknessPx=max(28,28)=28
        // barsExtentPx = balanced.length * 28 + 40 + (GROUPED_GRID_TOP_PX - DEFAULT_GRID_TOP_PX)
        //              = 5 * 28 + 40 + (48 - 16) = 140 + 40 + 32 = 212
        const series: CategoryCountSeries[] = [
            { id: 'a', label: 'Series A', data: balanced },
            { id: 'b', label: 'Series B', data: balanced }
        ];
        render(BarChart, { props: { data: balanced, orientation: 'horizontal', series } });
        const canvas = screen.getByTestId('bar-chart').firstElementChild as HTMLElement;
        expect(canvas).toHaveStyle({ height: '212px' });
    });
});
