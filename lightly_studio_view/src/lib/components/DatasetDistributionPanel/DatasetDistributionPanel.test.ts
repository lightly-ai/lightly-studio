import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import DatasetDistributionPanel from './DatasetDistributionPanel.svelte';
import { balanced, empty, longTail } from '../BarChart/fixtures';
import type { DistributionSource } from './types';

const echartsMock = vi.hoisted(() => {
    const instance = {
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn()
    };
    return { init: vi.fn(() => instance), instance };
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

const defaultProps = { data: balanced };

describe('DatasetDistributionPanel', () => {
    afterEach(() => {
        // bits-ui dialogs portal into the body and can leave styles behind.
        document.body.innerHTML = '';
        document.body.style.pointerEvents = '';
    });

    it('renders the title and the class/annotation summary', () => {
        render(DatasetDistributionPanel, { props: defaultProps });

        expect(screen.getByText('Class distribution')).toBeInTheDocument();
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

        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            xAxis: { data: string[] };
        };
        expect(option.xAxis.data).toEqual(['person', 'dog', 'car']);
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

        expect(
            (echartsMock.instance.setOption.mock.lastCall?.[0] as { yAxis: { type: string } }).yAxis
                .type
        ).toBe('value');

        await fireEvent.click(screen.getByTestId('dataset-distribution-toggle-orientation'));

        await waitFor(() =>
            expect(
                (echartsMock.instance.setOption.mock.lastCall?.[0] as { yAxis: { type: string } })
                    .yAxis.type
            ).toBe('category')
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

        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            xAxis: { data: string[] };
        };
        expect(option.xAxis.data).toEqual(['car']);
    });

    it('omits the source selector when only one source is available', () => {
        render(DatasetDistributionPanel, { props: defaultProps });
        expect(screen.queryByTestId('dataset-distribution-source-select')).not.toBeInTheDocument();
    });

    it('renders a close button only when onClose is provided and forwards clicks', async () => {
        const onClose = vi.fn();
        render(DatasetDistributionPanel, { props: { ...defaultProps, onClose } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-close-button'));

        expect(onClose).toHaveBeenCalledOnce();
    });
});
