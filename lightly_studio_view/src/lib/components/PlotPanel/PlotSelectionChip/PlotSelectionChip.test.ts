import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PlotSelectionChip from './PlotSelectionChip.svelte';

describe('PlotSelectionChip', () => {
    const defaultProps = { count: 1204, itemLabel: 'image', onClear: vi.fn() };

    it('shows the count with a singular or plural label', async () => {
        const { rerender } = render(PlotSelectionChip, defaultProps);
        const chip = screen.getByTestId('plot-selection-chip');
        expect(chip).toHaveTextContent('Plot filter: 1204 images');

        await rerender({ ...defaultProps, count: 1, itemLabel: 'video' });
        expect(chip).toHaveTextContent('Plot filter: 1 video');
    });

    it('calls onClear when the clear button is clicked', async () => {
        const onClear = vi.fn();
        render(PlotSelectionChip, { ...defaultProps, onClear });

        await fireEvent.click(screen.getByRole('button', { name: 'Clear plot filter' }));

        expect(onClear).toHaveBeenCalledOnce();
    });
});
