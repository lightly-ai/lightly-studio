import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PlotSelectionChip from './PlotSelectionChip.svelte';

describe('PlotSelectionChip', () => {
    const defaultProps = {
        selectionKind: 'region' as const,
        count: 1204,
        itemLabel: 'image',
        onClear: vi.fn(),
        pickHint: null
    };

    it('shows a region count with a singular or plural label, and a pick count', async () => {
        const { rerender } = render(PlotSelectionChip, defaultProps);
        const chip = screen.getByTestId('plot-selection-chip');
        expect(chip).toHaveTextContent('1204 images');

        await rerender({ ...defaultProps, count: 1, itemLabel: 'video' });
        expect(chip).toHaveTextContent('1 video');

        await rerender({ ...defaultProps, selectionKind: 'picks', count: 3 });
        expect(chip).toHaveTextContent('3 picked');
    });

    it('calls onClear when the clear button is clicked', async () => {
        const onClear = vi.fn();
        render(PlotSelectionChip, { ...defaultProps, onClear });

        await fireEvent.click(screen.getByRole('button', { name: 'Clear plot filter' }));

        expect(onClear).toHaveBeenCalledOnce();
    });

    it('shows only the hint when nothing is selected', () => {
        render(PlotSelectionChip, { ...defaultProps, selectionKind: null, pickHint: 'pick' });

        expect(screen.getByTestId('plot-selection-chip')).toHaveTextContent(
            'Shift + click to pick'
        );
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
});
