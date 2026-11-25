import { render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { makeClassMetrics, makeComparedRun } from '../fixtures';
import PerClassMetricSection from './PerClassMetricSection.svelte';

// jsdom has no canvas, so the bar chart gets a fake ECharts instance.
vi.mock('echarts/core', () => ({
    init: vi.fn(() => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn(), on: vi.fn() })),
    use: vi.fn()
}));
vi.mock('echarts/charts', () => ({ BarChart: {} }));
vi.mock('echarts/components', () => ({
    GridComponent: {},
    LegendComponent: {},
    TooltipComponent: {}
}));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

const CLASS_COUNT = 12;
// Class N has AP 0.9 in run-a and 0.9 - N/20 in run-b, so a higher N has a larger gap.
const classLabels = Array.from({ length: CLASS_COUNT }, (_, index) => `class-${index + 1}`);
const runAClasses = classLabels.map((label) => makeClassMetrics(label, 0.9));
const runBClasses = classLabels.map((label, index) => makeClassMetrics(label, 0.9 - index / 20));

const defaultProps = {
    taskType: 'object_detection' as const,
    runs: [
        makeComparedRun('run-a', {
            per_class: [makeClassMetrics('cat', 0.9), makeClassMetrics('dog', 0.4)]
        }),
        makeComparedRun('run-b', { per_class: [makeClassMetrics('cat', 0.7)] })
    ]
};

const manyClassesProps = {
    ...defaultProps,
    runs: [
        makeComparedRun('run-a', { per_class: runAClasses }),
        makeComparedRun('run-b', { per_class: runBClasses })
    ]
};

const bodyRows = () => within(screen.getByRole('table')).getAllByRole('row').slice(1);

describe('PerClassMetricSection', () => {
    beforeAll(() => {
        // The class count select needs pointer capture, which jsdom does not have.
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
    });

    it('shows the bar chart of the 10 classes with the largest gap by default', () => {
        render(PerClassMetricSection, { props: manyClassesProps });

        expect(screen.getByRole('tab', { name: 'Bar chart' })).toHaveAttribute(
            'aria-selected',
            'true'
        );
        expect(screen.queryByRole('table')).not.toBeInTheDocument();
        expect(screen.getByTestId('per-class-shown-count')).toHaveTextContent(
            '10 of 12 annotation classes with the largest gap between runs'
        );
    });

    it('shows average precision and the gap per annotation class in the heatmap', async () => {
        const user = userEvent.setup();
        render(PerClassMetricSection, { props: defaultProps });

        await user.click(screen.getByRole('tab', { name: 'Heatmap' }));

        expect(screen.getByRole('tab', { name: 'AP' })).toHaveAttribute('aria-selected', 'true');
        const headers = within(screen.getByRole('table'))
            .getAllByRole('columnheader')
            .map((cell) => cell.textContent?.trim());
        expect(headers).toEqual(['Annotation class', 'run-a', 'run-b', 'Gap']);
        const [catRow, dogRow] = bodyRows();
        expect(catRow).toHaveTextContent('cat0.9000.7000.200');
        expect(dogRow).toHaveTextContent('dog0.400—0.000');
    });

    it('ranks the heatmap rows by gap and shows all classes on request', async () => {
        const user = userEvent.setup();
        render(PerClassMetricSection, { props: manyClassesProps });
        await user.click(screen.getByRole('tab', { name: 'Heatmap' }));

        expect(bodyRows()).toHaveLength(10);
        expect(bodyRows()[0]).toHaveTextContent('class-12');

        await user.click(screen.getByTestId('per-class-limit'));
        await user.click(await waitFor(() => screen.getByRole('option', { name: 'All classes' })));

        await waitFor(() => expect(bodyRows()).toHaveLength(CLASS_COUNT));
    });

    it('switches the heatmap to another metric', async () => {
        const user = userEvent.setup();
        render(PerClassMetricSection, { props: defaultProps });
        await user.click(screen.getByRole('tab', { name: 'Heatmap' }));

        await user.click(screen.getByRole('tab', { name: 'Recall' }));

        const catRow = within(screen.getByRole('table')).getByRole('row', { name: /cat/ });
        expect(catRow).toHaveTextContent('0.500');
        expect(catRow).not.toHaveTextContent('0.900');
    });
});
