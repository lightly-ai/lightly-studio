import { render, screen } from '@testing-library/svelte';
import { expect, it, vi } from 'vitest';
import { SVGRenderer } from 'echarts/renderers';
import ConfusionMatrixPanel from './ConfusionMatrixPanel/ConfusionMatrixPanel.svelte';
import { small3Classes } from './fixtures';

vi.mock('echarts/core', async (importOriginal) => {
    const echarts = await importOriginal<typeof import('echarts/core')>();
    echarts.use([SVGRenderer]);
    return {
        ...echarts,
        init: (container: HTMLDivElement) =>
            echarts.init(container, null, { renderer: 'svg', width: 400, height: 320 })
    };
});

// ECharts measures labels with a canvas even when rendering SVG; jsdom has no 2D context.
vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation((() => ({
    measureText: (text: string) => ({ width: text.length * 6 })
})) as unknown as typeof HTMLCanvasElement.prototype.getContext);

it('renders the confusion matrix cells and axes with the real chart engine', () => {
    render(ConfusionMatrixPanel, { props: { matrix: small3Classes } });
    const container = screen.getByTestId('confusion-matrix');
    expect(container.querySelector('svg path')).toBeInTheDocument();
    expect(container).toHaveTextContent('Prediction');
    expect(container).toHaveTextContent('Ground Truth');
});
