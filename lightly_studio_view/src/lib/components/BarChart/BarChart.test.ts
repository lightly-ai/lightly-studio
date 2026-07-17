import { render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import BarChart from './BarChart.svelte';
import { balanced, empty } from './fixtures';

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
        expect(screen.getByTestId('bar-chart-empty')).toHaveTextContent('No data to display.');
    });

    it('renders a custom emptyState snippet instead of the default message', () => {
        const emptyState = createRawSnippet(() => ({
            render: () => '<span data-testid="custom-empty">Custom empty message</span>'
        }));
        render(BarChart, { props: { data: empty, emptyState } });
        expect(screen.getByTestId('custom-empty')).toBeInTheDocument();
        expect(screen.queryByText('No data to display.')).not.toBeInTheDocument();
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
});
