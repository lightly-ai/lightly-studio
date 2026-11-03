import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PlotSelectionChip from './PlotSelectionChip.svelte';

describe('PlotSelectionChip', () => {
    const defaultProps = { count: 1204, itemLabel: 'image', onClear: vi.fn() };

    it('shows the plural count', () => {
        render(PlotSelectionChip, defaultProps);

        expect(screen.getByTestId('plot-selection-chip')).toHaveTextContent(
            'Region filter: 1204 images'
        );
    });

    it('shows the singular count', () => {
        render(PlotSelectionChip, { ...defaultProps, count: 1, itemLabel: 'video' });

        expect(screen.getByTestId('plot-selection-chip')).toHaveTextContent(
            'Region filter: 1 video'
        );
    });

    it('calls onClear when the clear button is clicked', async () => {
        const onClear = vi.fn();
        render(PlotSelectionChip, { ...defaultProps, onClear });

        await fireEvent.click(screen.getByRole('button', { name: 'Clear region filter' }));

        expect(onClear).toHaveBeenCalledOnce();
    });
});
