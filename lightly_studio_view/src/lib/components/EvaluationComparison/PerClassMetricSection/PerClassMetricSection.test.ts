import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { makeClassMetrics, makeComparedRun } from '../fixtures';
import PerClassMetricSection from './PerClassMetricSection.svelte';

const defaultProps = {
    taskType: 'object_detection' as const,
    runs: [
        makeComparedRun('run-a', {
            per_class: [makeClassMetrics('cat', 0.9), makeClassMetrics('dog', 0.4)]
        }),
        makeComparedRun('run-b', { per_class: [makeClassMetrics('cat', 0.7)] })
    ]
};

describe('PerClassMetricSection', () => {
    it('shows average precision per annotation class by default', () => {
        render(PerClassMetricSection, { props: defaultProps });

        expect(screen.getByRole('tab', { name: 'AP' })).toHaveAttribute('aria-selected', 'true');
        const table = screen.getByRole('table');
        const headers = within(table)
            .getAllByRole('columnheader')
            .map((cell) => cell.textContent?.trim());
        expect(headers).toEqual(['Annotation class', 'run-a', 'run-b']);
        const dogRow = within(table).getByRole('row', { name: /dog/ });
        expect(dogRow).toHaveTextContent('0.400');
        expect(dogRow).toHaveTextContent('—');
    });

    it('switches the table to another metric', async () => {
        const user = userEvent.setup();
        render(PerClassMetricSection, { props: defaultProps });

        await user.click(screen.getByRole('tab', { name: 'Recall' }));

        const catRow = within(screen.getByRole('table')).getByRole('row', { name: /cat/ });
        expect(catRow).toHaveTextContent('0.500');
        expect(catRow).not.toHaveTextContent('0.900');
    });
});
