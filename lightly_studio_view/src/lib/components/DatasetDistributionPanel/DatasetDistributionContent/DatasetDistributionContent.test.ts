import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import DatasetDistributionContent from './DatasetDistributionContent.svelte';
import { useDistributionPanel } from '../useDistributionPanel.svelte';
import type { DistributionSource } from '../types';

const echartsMock = vi.hoisted(() => {
    let clickHandler: ((params: { dataIndex?: number }) => void) | undefined;
    const zrHandlers: Record<string, (event: { offsetX: number; offsetY: number }) => void> = {};
    const instance = {
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn((event: string, handler: (params: { dataIndex?: number }) => void) => {
            if (event === 'click') clickHandler = handler;
        }),
        convertFromPixel: vi.fn((_finder: unknown, offsetX: number) => offsetX / 100),
        getZr: () => ({
            on: vi.fn(
                (event: string, handler: (e: { offsetX: number; offsetY: number }) => void) => {
                    zrHandlers[event] = handler;
                }
            ),
            off: vi.fn()
        })
    };
    return {
        init: vi.fn(() => instance),
        instance,
        getClickHandler: () => clickHandler,
        zrHandlers
    };
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

const renderContent = (sources: DistributionSource[], overrides: Record<string, unknown> = {}) => {
    const panel = useDistributionPanel(() => ({ sources }));
    return render(DatasetDistributionContent, { props: { panel, ...overrides } });
};

describe('DatasetDistributionContent', () => {
    it('renders a bar chart for bar data', () => {
        renderContent([{ id: 'classes', label: 'Classes', data: [{ label: 'car', count: 10 }] }]);
        expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
        expect(screen.queryByTestId('histogram')).not.toBeInTheDocument();
    });

    it('renders the empty chart state when no data', () => {
        renderContent([{ id: 'classes', label: 'Classes', data: [] }]);
        expect(screen.getByTestId('bar-chart-empty')).toBeInTheDocument();
    });

    it('renders a histogram for a histogram group', () => {
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                valueNoun: 'samples',
                groups: [
                    {
                        id: 'confidence',
                        label: 'confidence',
                        histogram: { binEdges: [0, 0.5, 1], counts: [30, 70] }
                    }
                ]
            }
        ];
        renderContent(sources);
        expect(screen.getByTestId('histogram')).toBeInTheDocument();
        expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
    });

    it('renders a bar chart for categorical data', () => {
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groups: [
                    {
                        id: 'city',
                        label: 'city',
                        categorical: {
                            selectedValues: [],
                            buckets: [
                                {
                                    id: 'zurich',
                                    kind: 'value',
                                    value: 'Zurich',
                                    label: 'Zurich',
                                    count: 4
                                }
                            ]
                        }
                    }
                ]
            }
        ];
        renderContent(sources);
        expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    });

    it('forwards onBarClick when a bar is clicked', () => {
        const onBarClick = vi.fn();
        renderContent([{ id: 'classes', label: 'Classes', data: [{ label: 'car', count: 10 }] }], {
            onBarClick
        });
        echartsMock.getClickHandler()?.({ dataIndex: 0 });
        expect(onBarClick).toHaveBeenCalledOnce();
    });

    it('forwards onHistogramRangeSelect with the group id when a histogram range is selected', () => {
        const onHistogramRangeSelect = vi.fn();
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groups: [
                    {
                        id: 'confidence',
                        label: 'confidence',
                        histogram: { binEdges: [0, 0.5, 1], counts: [30, 70] }
                    }
                ]
            }
        ];
        renderContent(sources, { onHistogramRangeSelect });
        echartsMock.zrHandlers.mousedown({ offsetX: 150, offsetY: 10 });
        window.dispatchEvent(new MouseEvent('mouseup'));
        expect(onHistogramRangeSelect).toHaveBeenCalledWith('confidence', { min: 0.5, max: 1 });
    });

    it('shows the loading status when categorical buckets are empty and loading', () => {
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groups: [
                    {
                        id: 'city',
                        label: 'city',
                        categorical: { buckets: [], selectedValues: [], loading: true }
                    }
                ]
            }
        ];
        renderContent(sources);
        expect(screen.getByRole('status')).toHaveTextContent('Loading metadata distribution');
    });

    it('shows the error alert with retry when categorical buckets are empty and there is an error', async () => {
        const onCategoricalRetry = vi.fn();
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groups: [
                    {
                        id: 'city',
                        label: 'city',
                        categorical: {
                            buckets: [],
                            selectedValues: ['Zurich'],
                            error: 'network failure'
                        }
                    }
                ]
            }
        ];
        renderContent(sources, { onCategoricalRetry });
        expect(screen.getByRole('alert')).toHaveTextContent('Could not load metadata distribution');
        await fireEvent.click(screen.getByTestId('metadata-categorical-retry'));
        expect(onCategoricalRetry).toHaveBeenCalledOnce();
    });
});
