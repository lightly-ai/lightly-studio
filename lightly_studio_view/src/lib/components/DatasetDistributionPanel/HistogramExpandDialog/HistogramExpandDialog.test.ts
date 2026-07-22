import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import HistogramExpandDialog from './HistogramExpandDialog.svelte';
import type { HistogramData } from '$lib/components/Histogram';

const echartsMock = vi.hoisted(() => {
    const instance = {
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn(),
        getZr: () => ({ on: vi.fn(), off: vi.fn() })
    };
    return { init: vi.fn(() => instance), instance };
});

vi.mock('echarts/core', () => ({
    init: echartsMock.init,
    use: vi.fn()
}));
vi.mock('echarts/charts', () => ({ CustomChart: {} }));
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

const data: HistogramData = { binEdges: [0, 0.5, 1], counts: [30, 70] };

const renderDialog = (overrides = {}) => {
    const onBinCountChange = vi.fn();
    render(HistogramExpandDialog, {
        props: {
            open: true,
            data,
            label: 'confidence',
            binCount: 20,
            onBinCountChange,
            ...overrides
        }
    });
    return { onBinCountChange };
};

describe('HistogramExpandDialog', () => {
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

    it('renders the title with the field label', () => {
        renderDialog();

        expect(screen.getByText('Distribution · confidence')).toBeInTheDocument();
    });

    it('renders nothing while closed', () => {
        renderDialog({ open: false });

        expect(screen.queryByText('Distribution · confidence')).not.toBeInTheDocument();
    });

    it('shows the summary with total count, bin count, and range', () => {
        renderDialog();

        expect(
            screen.getByTestId('dataset-distribution-expanded-histogram-summary')
        ).toHaveTextContent('100 samples · 2 bins · 0–1');
    });

    it('hides the bin-count selector when no change handler is provided', () => {
        renderDialog({ onBinCountChange: undefined });

        expect(
            screen.queryByTestId('dataset-distribution-expanded-bin-count')
        ).not.toBeInTheDocument();
    });

    it('shows the bin-count selector with the applied bin count', () => {
        renderDialog({ binCount: 50 });

        expect(screen.getByTestId('dataset-distribution-expanded-bin-count')).toHaveTextContent(
            '50 bins'
        );
    });

    it('calls onBinCountChange with the selected count when the user picks a new value', async () => {
        const { onBinCountChange } = renderDialog({ binCount: 20 });
        const user = userEvent.setup();

        await user.click(screen.getByTestId('dataset-distribution-expanded-bin-count'));
        const option = await waitFor(() => screen.getByRole('option', { name: '10 bins' }));
        await user.click(option);

        expect(onBinCountChange).toHaveBeenCalledWith(10);
    });
});
