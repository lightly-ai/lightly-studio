import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import DistributionChart from './DistributionChart.svelte';
import type { HistogramData } from '$lib/components/Histogram';
import type { DistributionConfig } from '../types';
import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
import type { CategoryCount } from '$lib/components/BarChart';

const echartsMock = vi.hoisted(() => {
    const instance = {
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn(),
        convertFromPixel: vi.fn(),
        getZr: () => ({ on: vi.fn(), off: vi.fn() })
    };
    return { init: vi.fn(() => instance), instance };
});

vi.mock('echarts/core', () => ({ init: echartsMock.init, use: vi.fn() }));
vi.mock('echarts/charts', () => ({ BarChart: {}, CustomChart: {} }));
vi.mock('echarts/components', () => ({ GridComponent: {}, TooltipComponent: {} }));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
    } as unknown as typeof ResizeObserver;
}

const histogram: HistogramData = { binEdges: [0, 0.5, 1], counts: [30, 70] };

const viewConfig: DistributionConfig = {
    mode: 'topN',
    n: 10,
    sortBy: 'count',
    manualClasses: [],
    orientation: 'horizontal'
};

const barData: CategoryCount[] = [
    { label: 'cat', count: 10 },
    { label: 'dog', count: 5 }
];

const buckets: CategoricalMetadataBucket[] = [
    { id: 'a', kind: 'value', value: 'red', label: 'Red', count: 8 },
    { id: 'b', kind: 'missing', value: null, label: 'Missing', count: 2 }
];

const defaultProps = {
    activeHistogram: null,
    activeCategorical: null,
    viewConfig,
    visible: barData,
    totalCount: 15,
    selectedRange: undefined,
    onHistogramRangeSelect: undefined,
    onBarClick: undefined,
    onCategoricalRetry: undefined
};

describe('DistributionChart', () => {
    it('renders the bar chart when there is no active histogram or categorical data', () => {
        render(DistributionChart, { props: defaultProps });

        expect(echartsMock.instance.setOption).toHaveBeenCalled();
    });

    it('renders the histogram when activeHistogram is provided', () => {
        echartsMock.instance.setOption.mockClear();
        render(DistributionChart, { props: { ...defaultProps, activeHistogram: histogram } });

        expect(echartsMock.instance.setOption).toHaveBeenCalled();
    });

    it('shows the loading state when categorical is loading with no buckets', () => {
        render(DistributionChart, {
            props: {
                ...defaultProps,
                activeCategorical: { buckets: [], selectedValues: [], loading: true }
            }
        });

        expect(screen.getByRole('status')).toHaveTextContent('Loading metadata distribution…');
    });

    it('shows the error state with retry when categorical errors with no buckets', () => {
        const onCategoricalRetry = vi.fn();
        render(DistributionChart, {
            props: {
                ...defaultProps,
                activeCategorical: {
                    buckets: [],
                    selectedValues: [],
                    error: 'Failed to load'
                },
                onCategoricalRetry
            }
        });

        expect(screen.getByRole('alert')).toHaveTextContent(
            'Could not load metadata distribution.'
        );
        expect(screen.getByTestId('metadata-categorical-retry')).toBeInTheDocument();
    });

    it('calls onCategoricalRetry when the retry button is clicked', async () => {
        const onCategoricalRetry = vi.fn();
        render(DistributionChart, {
            props: {
                ...defaultProps,
                activeCategorical: { buckets: [], selectedValues: [], error: 'oops' },
                onCategoricalRetry
            }
        });

        await fireEvent.click(screen.getByTestId('metadata-categorical-retry'));

        expect(onCategoricalRetry).toHaveBeenCalledOnce();
    });

    it('hides the retry button in the error state when no handler is provided', () => {
        render(DistributionChart, {
            props: {
                ...defaultProps,
                activeCategorical: { buckets: [], selectedValues: [], error: 'oops' }
            }
        });

        expect(screen.queryByTestId('metadata-categorical-retry')).not.toBeInTheDocument();
    });

    it('renders a sr-only accessibility list for categorical buckets', () => {
        render(DistributionChart, {
            props: {
                ...defaultProps,
                activeCategorical: { buckets, selectedValues: [] }
            }
        });

        const list = screen.getByRole('list', { name: 'Categorical metadata value counts' });
        expect(list).toBeInTheDocument();
        expect(list.querySelectorAll('li')).toHaveLength(2);
    });

    it('marks selected categorical values in the accessibility list', () => {
        render(DistributionChart, {
            props: {
                ...defaultProps,
                activeCategorical: { buckets, selectedValues: ['red'] }
            }
        });

        const items = screen
            .getByRole('list', { name: 'Categorical metadata value counts' })
            .querySelectorAll('li');
        expect(items[0].textContent).toContain(', selected');
        expect(items[1].textContent).not.toContain(', selected');
    });

    it('falls through to the bar chart when categorical has buckets but is still loading', () => {
        echartsMock.instance.setOption.mockClear();
        render(DistributionChart, {
            props: {
                ...defaultProps,
                activeCategorical: { buckets, selectedValues: [], loading: true }
            }
        });

        // Loading spinner only appears for the zero-bucket case; with buckets the bar chart renders.
        expect(screen.queryByRole('status')).not.toBeInTheDocument();
        expect(echartsMock.instance.setOption).toHaveBeenCalled();
    });
});
