import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import DatasetDistributionPanel from './DatasetDistributionPanel.svelte';
import { balanced, empty, longTail } from '../BarChart/fixtures';
import type { DistributionSource } from './types';
import { AnnotationCountMode, AnnotationType } from '$lib/api/lightly_studio_local/types.gen';

const echartsMock = vi.hoisted(() => {
    const zrHandlers: Record<string, (event: { offsetX: number; offsetY: number }) => void> = {};
    const instance = {
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn(),
        // 2 bins across a 200px-wide canvas → 100px per bin index.
        convertFromPixel: vi.fn((_finder: unknown, offsetX: number) => offsetX / 100),
        getZr: () => ({
            on: (event: string, handler: (event: { offsetX: number; offsetY: number }) => void) => {
                zrHandlers[event] = handler;
            },
            off: vi.fn()
        })
    };
    return { init: vi.fn(() => instance), instance, zrHandlers };
});

vi.mock('echarts/core', () => ({
    init: echartsMock.init,
    use: vi.fn()
}));
vi.mock('echarts/charts', () => ({ BarChart: {}, CustomChart: {} }));
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

const defaultProps = { data: balanced };

describe('DatasetDistributionPanel', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
    });

    afterEach(() => {
        // bits-ui dialogs portal into the body and can leave styles behind.
        document.body.innerHTML = '';
        document.body.style.pointerEvents = '';
    });

    it('renders the title and the class/annotation summary', () => {
        render(DatasetDistributionPanel, { props: defaultProps });

        expect(screen.getByText('Distribution')).toBeInTheDocument();
        expect(
            screen.getByText('5 classes · sorted by count · 491 annotations')
        ).toBeInTheDocument();
    });

    it('summarizes a top-N subset when there are more classes than topN', () => {
        render(DatasetDistributionPanel, { props: { data: longTail, topN: 10 } });

        expect(screen.getByText(/Top 10 of 30 classes · sorted by count/)).toBeInTheDocument();
    });

    it('omits the summary and shows the chart empty state without data', () => {
        render(DatasetDistributionPanel, { props: { data: empty } });

        expect(screen.queryByText(/classes ·/)).not.toBeInTheDocument();
        expect(screen.getByTestId('bar-chart-empty')).toBeInTheDocument();
    });

    it('passes counts to the chart sorted descending', () => {
        const unsorted = [
            { label: 'car', count: 3 },
            { label: 'person', count: 10 },
            { label: 'dog', count: 7 }
        ];
        render(DatasetDistributionPanel, { props: { data: unsorted } });

        // Horizontal default: categories live on the y-axis.
        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            yAxis: { data: string[] };
        };
        expect(option.yAxis.data).toEqual(['person', 'dog', 'car']);
    });

    it('applies a new top-N from the config dialog', async () => {
        render(DatasetDistributionPanel, { props: { data: longTail } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));
        const input = await waitFor(() => screen.getByTestId('distribution-config-top-n'));
        await fireEvent.input(input, { target: { value: '5' } });
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        await waitFor(() =>
            expect(screen.getByText(/Top 5 of 30 classes · sorted by count/)).toBeInTheDocument()
        );
    });

    it('shows all classes via the header quick action, which then hides itself', async () => {
        render(DatasetDistributionPanel, { props: { data: longTail, topN: 10 } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-show-all'));

        await waitFor(() =>
            expect(screen.getByText(/30 classes · sorted by count/)).toBeInTheDocument()
        );
        expect(screen.queryByTestId('dataset-distribution-show-all')).not.toBeInTheDocument();
    });

    it('applies a new top-N from the expanded view and keeps it in sync with the panel', async () => {
        render(DatasetDistributionPanel, { props: { data: longTail } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-expand'));
        const configure = await waitFor(() =>
            screen.getByTestId('dataset-distribution-expanded-configure')
        );
        await fireEvent.click(configure);
        const input = await waitFor(() => screen.getByTestId('distribution-config-top-n'));
        await fireEvent.input(input, { target: { value: '5' } });
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        // Both the expanded view's header and the panel header reflect the new config.
        await waitFor(() =>
            expect(screen.getAllByText(/Top 5 of 30 classes · sorted by count/)).toHaveLength(2)
        );
    });

    it('toggles the chart orientation from the header', async () => {
        render(DatasetDistributionPanel, { props: defaultProps });

        // Defaults to horizontal bars (categories on the y-axis) to avoid the
        // initial horizontal scroll.
        expect(
            (echartsMock.instance.setOption.mock.lastCall?.[0] as { yAxis: { type: string } }).yAxis
                .type
        ).toBe('category');

        await fireEvent.click(screen.getByTestId('dataset-distribution-toggle-orientation'));

        await waitFor(() =>
            expect(
                (echartsMock.instance.setOption.mock.lastCall?.[0] as { yAxis: { type: string } })
                    .yAxis.type
            ).toBe('value')
        );
    });

    it('shows the source selector and switches the charted data between sources', async () => {
        const sources: DistributionSource[] = [
            {
                id: 'class',
                label: 'Class labels',
                data: [{ label: 'car', count: 10 }],
                valueNoun: 'annotations'
            },
            {
                id: 'tags',
                label: 'Tags',
                data: [{ label: 'reviewed', count: 42 }],
                valueNoun: 'samples'
            }
        ];
        render(DatasetDistributionPanel, { props: { sources } });

        // Default source is the first one (class labels).
        expect(screen.getByText(/1 class · sorted by count · 10 annotations/)).toBeInTheDocument();

        // The source selector is present; a single-source panel would not show it.
        expect(screen.getByTestId('dataset-distribution-source-select')).toBeInTheDocument();

        // Horizontal default: categories live on the y-axis.
        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            yAxis: { data: string[] };
        };
        expect(option.yAxis.data).toEqual(['car']);
    });

    it('omits the source selector when only one source is available', () => {
        render(DatasetDistributionPanel, { props: defaultProps });
        expect(screen.queryByTestId('dataset-distribution-source-select')).not.toBeInTheDocument();
    });

    it('defaults to the first source with content when a leading source is empty', () => {
        const sources: DistributionSource[] = [
            { id: 'all', label: 'All types', data: [], valueNoun: 'annotations' },
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
        render(DatasetDistributionPanel, { props: { sources } });

        // The empty "All types" source is skipped in favour of metadata.
        expect(screen.getByTestId('histogram')).toBeInTheDocument();
        expect(screen.getByTestId('dataset-distribution-histogram-summary')).toHaveTextContent(
            '100 samples · 2 bins · 0–1'
        );
    });

    it('renders a close button only when onClose is provided and forwards clicks', async () => {
        const onClose = vi.fn();
        render(DatasetDistributionPanel, { props: { ...defaultProps, onClose } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-close-button'));

        expect(onClose).toHaveBeenCalledOnce();
    });

    it('shows the count by select in the config dialog with Objects selected by default', async () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: AnnotationType.OBJECT_DETECTION,
                        label: 'Object detection',
                        data: [{ label: 'car', count: 5 }]
                    }
                ]
            }
        });

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));

        const countBySelect = await waitFor(() =>
            screen.getByTestId('distribution-config-count-mode')
        );
        expect(countBySelect).toBeInTheDocument();
        expect(countBySelect).toHaveTextContent('Objects');
    });

    it('shows the count by select for All types source too', async () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: 'all',
                        label: 'All types',
                        data: [{ label: 'car', count: 5 }]
                    },
                    {
                        id: AnnotationType.OBJECT_DETECTION,
                        label: 'Object detection',
                        data: [{ label: 'car', count: 5 }]
                    }
                ]
            }
        });

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));

        await waitFor(() =>
            expect(screen.getByTestId('distribution-config-count-mode')).toBeInTheDocument()
        );
    });

    it('calls onCountModeChange when count mode changes via the config dialog', async () => {
        const user = userEvent.setup();
        const onCountModeChange = vi.fn();
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: AnnotationType.OBJECT_DETECTION,
                        label: 'Object detection',
                        data: [{ label: 'car', count: 5 }]
                    }
                ],
                onCountModeChange
            }
        });

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));
        const countBySelect = await waitFor(() =>
            screen.getByTestId('distribution-config-count-mode')
        );
        await user.click(countBySelect);
        const samplesOption = await waitFor(() => screen.getByRole('option', { name: 'Samples' }));
        await user.click(samplesOption);
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        expect(onCountModeChange).toHaveBeenCalledWith(AnnotationCountMode.SAMPLES);
    });

    it('hides the total count in the header when count mode is changed to Samples', async () => {
        const user = userEvent.setup();
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: AnnotationType.OBJECT_DETECTION,
                        label: 'Object detection',
                        data: [{ label: 'car', count: 10 }],
                        valueNoun: 'instances'
                    }
                ]
            }
        });

        expect(screen.getByText(/10 instances/)).toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));
        const countBySelect = await waitFor(() =>
            screen.getByTestId('distribution-config-count-mode')
        );
        await user.click(countBySelect);
        const samplesOption = await waitFor(() => screen.getByRole('option', { name: 'Samples' }));
        await user.click(samplesOption);
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        await waitFor(() => expect(screen.queryByText(/instances/)).not.toBeInTheDocument());
    });

    it('shows the total count in the header by default (Objects mode)', () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: AnnotationType.OBJECT_DETECTION,
                        label: 'Object detection',
                        data: [{ label: 'car', count: 10 }],
                        valueNoun: 'instances'
                    }
                ]
            }
        });

        expect(screen.getByText(/10 instances/)).toBeInTheDocument();
    });

    it('renders a histogram instead of a bar chart for a group carrying bins', () => {
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groupLabel: 'Metadata key',
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
        render(DatasetDistributionPanel, { props: { sources } });

        expect(screen.getByTestId('histogram')).toBeInTheDocument();
        expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
        // Categorical controls (sort / top-N / orientation) don't apply to bins.
        expect(screen.queryByText(/sorted by/)).not.toBeInTheDocument();
    });

    it('summarizes a histogram group with total count, bins and range', () => {
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
        render(DatasetDistributionPanel, { props: { sources } });

        expect(screen.getByTestId('dataset-distribution-histogram-summary')).toHaveTextContent(
            '100 samples · 2 bins · 0–1'
        );
    });

    it('forwards a histogram range selection as the group id and value interval', () => {
        const onHistogramRangeSelect = vi.fn();
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groupLabel: 'Metadata key',
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
        render(DatasetDistributionPanel, { props: { sources, onHistogramRangeSelect } });

        // Press and release over the second bin (offsetX 150 → index 1.5 → bin 1).
        echartsMock.zrHandlers.mousedown({ offsetX: 150, offsetY: 10 });
        window.dispatchEvent(new MouseEvent('mouseup'));

        expect(onHistogramRangeSelect).toHaveBeenCalledWith('confidence', { min: 0.5, max: 1 });
    });
});
