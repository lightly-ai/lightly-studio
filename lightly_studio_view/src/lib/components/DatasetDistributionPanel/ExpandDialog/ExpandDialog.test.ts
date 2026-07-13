import { fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ExpandDialog from './ExpandDialog.svelte';
import { longTail } from '../../BarChart/fixtures';
import type { DistributionConfig } from '../types';

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

const config: DistributionConfig = {
    mode: 'topN',
    n: 10,
    sortBy: 'count',
    manualClasses: [],
    orientation: 'vertical'
};

const renderDialog = (overrides = {}) => {
    const onConfigChange = vi.fn();
    render(ExpandDialog, {
        props: { open: true, data: longTail, config, onConfigChange, ...overrides }
    });
    return { onConfigChange };
};

describe('ExpandDialog', () => {
    afterEach(() => {
        // bits-ui dialogs portal into the body and can leave styles behind.
        document.body.innerHTML = '';
        document.body.style.pointerEvents = '';
    });

    it('renders the title and a top-N summary from the applied config', () => {
        renderDialog();

        expect(screen.getByText('Class distribution')).toBeInTheDocument();
        expect(screen.getByText(/Top 10 of 30 classes · sorted by count/)).toBeInTheDocument();
    });

    it('renders nothing while closed', () => {
        renderDialog({ open: false });

        expect(screen.queryByText('Class distribution')).not.toBeInTheDocument();
    });

    it('charts only the visible subset, sorted by count descending', () => {
        renderDialog();

        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            xAxis: { data: string[] };
        };
        expect(option.xAxis.data).toHaveLength(10);
        expect(option.xAxis.data[0]).toBe('person');
    });

    it('expands to all classes via the header quick action', async () => {
        const { onConfigChange } = renderDialog();

        await fireEvent.click(screen.getByTestId('dataset-distribution-expanded-show-all'));

        expect(onConfigChange).toHaveBeenCalledWith({ ...config, mode: 'topN', n: 30 });
    });

    it('toggles orientation via the header', async () => {
        const { onConfigChange } = renderDialog();

        await fireEvent.click(
            screen.getByTestId('dataset-distribution-expanded-toggle-orientation')
        );

        expect(onConfigChange).toHaveBeenCalledWith({ ...config, orientation: 'horizontal' });
    });
});
