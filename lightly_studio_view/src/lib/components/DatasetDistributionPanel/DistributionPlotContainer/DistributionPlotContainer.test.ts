import { render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it } from 'vitest';
import DistributionPlotContainer from './DistributionPlotContainer.svelte';

describe('DistributionPlotContainer', () => {
    it('preserves the plot while loading and restores interaction when complete', async () => {
        const children = createRawSnippet(() => ({ render: () => '<div>Current plot</div>' }));
        const view = render(DistributionPlotContainer, { loading: true, children });
        const plot = screen.getByText('Current plot');
        expect(screen.getByRole('status')).toHaveTextContent('Loading...');
        expect(plot.parentElement?.inert).toBe(true);
        expect(plot.closest('[aria-busy]')).toHaveAttribute('aria-busy', 'true');
        await view.rerender({ loading: false, children });
        expect(screen.getByText('Current plot')).toBe(plot);
        expect(plot.parentElement?.inert).toBe(false);
        expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });
});
