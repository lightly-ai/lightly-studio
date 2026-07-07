import { render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ExpandDialog from './ExpandDialog.svelte';
import { small3Classes } from '../../fixtures';
import type { ColorConfig } from '../../ClassSetDialog/types';

vi.mock('echarts/core', () => ({
    init: vi.fn(() => ({
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn()
    })),
    use: vi.fn()
}));
vi.mock('echarts/charts', () => ({ HeatmapChart: {} }));
vi.mock('echarts/components', () => ({
    TooltipComponent: {},
    VisualMapComponent: {},
    GridComponent: {},
    DataZoomInsideComponent: {}
}));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

const color: ColorConfig = { intensity: 1, logScale: true };

describe('ExpandDialog', () => {
    afterEach(() => {
        document.body.innerHTML = '';
    });

    it('renders the matrix and zoom hint when open', async () => {
        render(ExpandDialog, { props: { open: true, matrix: small3Classes, color } });

        await waitFor(() => expect(screen.getByText('Confusion matrix')).toBeInTheDocument());
        expect(screen.getByText(/Scroll or pinch inside the chart to zoom/)).toBeInTheDocument();
        expect(screen.getByTestId('confusion-matrix')).toBeInTheDocument();
    });

    it('renders nothing when closed', () => {
        render(ExpandDialog, { props: { open: false, matrix: small3Classes, color } });

        expect(screen.queryByText('Confusion matrix')).not.toBeInTheDocument();
    });
});
