import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import PanelDockToggle from './PanelDockToggle.svelte';

describe('PanelDockToggle', () => {
    it('moves a bottom panel to the right', async () => {
        const onChange = vi.fn();
        render(PanelDockToggle, { dock: 'bottom', label: 'camera projections', onChange });

        await fireEvent.click(
            screen.getByRole('button', { name: 'Show camera projections on the right' })
        );

        expect(onChange).toHaveBeenCalledWith('right');
    });

    it('moves a right panel to the bottom', async () => {
        const onChange = vi.fn();
        render(PanelDockToggle, { dock: 'right', label: 'camera projections', onChange });

        await fireEvent.click(
            screen.getByRole('button', { name: 'Show camera projections at the bottom' })
        );

        expect(onChange).toHaveBeenCalledWith('bottom');
    });
});
